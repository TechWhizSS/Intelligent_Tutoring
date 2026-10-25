"""Free ACE-Step music generation. No paid API, TTS or fabricated songs.

The model weights must be downloaded once. Inference runs on the host's own CPU
(or a configured GPU). Optionally connect the owner's official free GPU API.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import wave
from . import free_gpu

ROOT = Path(__file__).resolve().parents[1]
FREE_HOME = Path(os.getenv('FREE_MUSIC_HOME', ROOT / 'runtime/free-music')).resolve()
ENGINE = Path(os.getenv('FREE_MUSIC_ENGINE', FREE_HOME / 'acestep.cpp/build/ace-synth')).resolve()
MODELS = Path(os.getenv('FREE_MUSIC_MODELS', FREE_HOME / 'models')).resolve()
MUSIC_MODEL = 'acestep-v15-turbo-Q4_K_M'
MODEL_FILES = ['acestep-v15-turbo-Q4_K_M.gguf', 'Qwen3-Embedding-0.6B-Q8_0.gguf', 'vae-BF16.gguf']
LYRICS_MODEL = 'Local source-linked templates (editable; no LLM)'
MUSIC_PROVIDER_NAME = 'ACE-Step 1.5 local AI'
LOCK = threading.Lock()


class ProviderError(Exception):
    pass


def readiness():
    files = []
    for name in MODEL_FILES:
        path = MODELS / name
        valid = False
        try:
            if path.stat().st_size > 1024:
                with path.open('rb') as f:
                    valid = f.read(4) == b'GGUF'
        except OSError:
            pass
        files.append({'file': name, 'ready': valid})
    executable = ENGINE.is_file() and os.access(ENGINE, os.X_OK)
    return {'engineReady': executable, 'models': files, 'ready': executable and all(f['ready'] for f in files)}


def configured():
    try:
        if free_gpu.settings():
            return True
    except free_gpu.GPUError:
        return False
    return readiness()['ready']


def blocker():
    try:
        if free_gpu.settings():
            return None
    except free_gpu.GPUError as exc:
        return str(exc)
    status = readiness()
    missing = [f['file'] for f in status['models'] if not f['ready']]
    if status['ready']:
        return None
    parts = []
    if not status['engineReady']:
        parts.append('free ACE-Step engine not installed')
    if missing:
        parts.append('model weights not downloaded: ' + ', '.join(missing))
    return ('Free AI music setup is incomplete: ' + '; '.join(parts) + '. Run python3 scripts/setup_free_music.py. '
            'The first download needs Hugging Face network access; no payment or API key is required. No song was fabricated.')


def provider_name():
    return free_gpu.PROVIDER if free_gpu.settings() else MUSIC_PROVIDER_NAME


def music_model():
    return free_gpu.MODEL if free_gpu.settings() else MUSIC_MODEL


def save_connection(text=None, local=False):
    try:
        if local:
            free_gpu.disconnect()
        else:
            verified = free_gpu.save(text)
            return check(verified=verified)
        return check()
    except free_gpu.GPUError as exc:
        raise ProviderError(str(exc)) from None


def lyrics(topic, language, settings, approved):
    # Deliberately deterministic source-linked drafting; never pretend an LLM wrote it.
    from .content import demo_lyrics
    code = {'English': 'en', 'Hindi': 'hi', 'en': 'en', 'hi': 'hi'}.get(language)
    if code is None:
        raise ProviderError('Only English and Hindi are supported.')
    return demo_lyrics(topic, code)


def build_request(lyric_text, language, settings):
    if not isinstance(lyric_text, str) or not 1 <= len(lyric_text.strip()) <= 16000:
        raise ProviderError('Lyrics must contain 1–16000 characters.')
    code = {'English': 'en', 'Hindi': 'hi', 'en': 'en', 'hi': 'hi'}.get(language)
    if code is None:
        raise ProviderError('Only English and Hindi are supported.')
    duration = int(settings.get('length', 30))
    tempo = int(settings.get('tempo', 100))
    if not 10 <= duration <= 600 or not 30 <= tempo <= 300:
        raise ProviderError('ACE-Step duration or BPM is outside the supported range.')
    caption = (f"Original {settings.get('genre', 'Pop')} educational song, {settings.get('mood', 'Uplifting')} mood, "
               f"{settings.get('vocal', 'Warm')} sung vocals in {language}, clearly articulated singing, "
               'catchy repeated chorus, expressive melody, drums, bass and instrumental accompaniment. '
               'Sing the provided lyrics; this is a song, not spoken narration. '
               f"Formula repetition preference: {settings.get('formulaRepeats', 2)}. "
               f"Musical preferences: {settings.get('instructions', '')}")
    return {'caption': caption, 'lyrics': lyric_text, 'bpm': tempo, 'duration': duration,
            'keyscale': 'C major', 'timesignature': '4', 'vocal_language': code,
            'seed': -1, 'synth_batch_size': 1, 'inference_steps': 8,
            'task_type': 'text2music', 'output_format': 'wav16', 'synth_model': MUSIC_MODEL}


def validate_wav(data):
    try:
        with wave.open(io.BytesIO(data), 'rb') as f:
            if f.getnframes() < f.getframerate() or f.getnchannels() not in (1, 2):
                raise ValueError('empty or too short')
    except (wave.Error, EOFError, ValueError):
        raise ProviderError('The AI engine returned no usable WAV audio. No song was fabricated.') from None
    return data, 'audio/wav', ''


def music(lyric_text, language, settings):
    payload = build_request(lyric_text, language, settings)
    if not configured():
        raise ProviderError(blocker())
    if not LOCK.acquire(blocking=False):
        raise ProviderError('The free local music engine is busy. Please wait for the current song to finish.')
    try:
        if free_gpu.settings():
            try:
                data, words = free_gpu.render(payload)
                audio, mime, _ = validate_wav(data)
                return audio, mime, words
            except free_gpu.GPUError as exc:
                raise ProviderError(str(exc)) from None
        jobs = ROOT / 'runtime/music-jobs'
        jobs.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=jobs, prefix='song-') as temp:
            job = Path(temp)
            request_file = job / 'request.json'
            request_file.write_text(json.dumps(payload, ensure_ascii=False))
            command = [str(ENGINE), '--models', str(MODELS), '--request', str(request_file),
                       '--device', os.getenv('FREE_MUSIC_DEVICE', 'CPU'), '--vae-chunk', '256', '--vae-overlap', '32']
            env = {**os.environ, 'OMP_NUM_THREADS': os.getenv('FREE_MUSIC_THREADS', '2')}
            try:
                with (job / 'engine.log').open('wb') as log:
                    result = subprocess.run(command, cwd=job, env=env, stdout=log, stderr=subprocess.STDOUT,
                                            timeout=int(os.getenv('FREE_MUSIC_TIMEOUT', '1800')), check=False)
            except subprocess.TimeoutExpired:
                raise ProviderError('Local AI generation exceeded the CPU time limit. Try a 30-second song. No audio was fabricated.') from None
            except OSError:
                raise ProviderError('The free music engine could not start. Rebuild it with scripts/setup_free_music.py.') from None
            output = job / 'request0.wav'
            if result.returncode != 0 or not output.is_file():
                raise ProviderError(f'Local AI music generation failed (exit {result.returncode}). Check model files and available RAM. No song was fabricated.')
            if output.stat().st_size > 128_000_000:
                raise ProviderError('Generated audio is too large. Request a shorter song.')
            return validate_wav(output.read_bytes())
    finally:
        LOCK.release()


def check(verified=None):
    try:
        if free_gpu.settings():
            result = {'provider': free_gpu.PROVIDER, 'configured': True, 'lyricsModel': LYRICS_MODEL,
                      'musicModel': free_gpu.MODEL, 'liveAudioVerified': False, 'listeningVerified': False,
                      'price': 'Owner-run free GPU; Colab availability and session limits apply',
                      'mode': 'GPU configured; authenticated check required'}
            try:
                verified = verified or free_gpu.probe()
                result['checks'] = [{'status': 'authenticated; generation unverified', **verified}]
                result['mode'] = 'GPU API authenticated; generation unverified'
            except free_gpu.GPUError as exc:
                result['configured'] = False
                result['checks'] = [{'status': 'blocked', 'reason': str(exc)}]
            return result
    except free_gpu.GPUError as exc:
        return {'configured': False, 'liveAudioVerified': False, 'listeningVerified': False,
                'checks': [{'status': 'blocked', 'reason': str(exc)}]}
    status = readiness()
    return {'provider': MUSIC_PROVIDER_NAME, 'configured': status['ready'], 'lyricsModel': LYRICS_MODEL,
            'musicModel': MUSIC_MODEL, 'liveAudioVerified': False, 'listeningVerified': False,
            'price': 'No paid API; runs locally using your host compute',
            'mode': 'free local AI ready' if status['ready'] else 'free setup required',
            'checks': [{'model': MUSIC_MODEL, 'status': 'ready; generation unverified' if status['ready'] else 'blocked',
                        'reason': blocker(), **status}]}
