"""Official ACE-Step REST protocol, as used by the uploaded Android project.

Only an owner's loopback service or key-protected Cloudflare quick tunnel is
accepted. This is an optional, owner-run free GPU; never a shared paid service.
"""
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path(os.getenv('APP_DATA_DIR', Path(__file__).resolve().parents[1] / 'runtime')) / 'music-service.json'
PROVIDER = 'ACE-Step 1.5 connected GPU'
MODEL = 'acestep-v15-turbo'


class GPUError(Exception):
    pass


def validate(url, key):
    if not isinstance(url, str) or not isinstance(key, str):
        raise GPUError('The GPU URL and connection key must be text.')
    url, key = url.strip().rstrip('/'), key.strip()
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        raise GPUError('Invalid GPU service URL.') from None
    if p.username or p.password or p.path or p.query or p.fragment:
        raise GPUError('Use only the GPU service origin, without a path, query or embedded credentials.')
    try:
        local = p.scheme == 'http' and p.hostname in ('127.0.0.1', 'localhost') and p.port == 8001
        tunnel = p.scheme == 'https' and p.port in (None, 443) and bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com', p.hostname or ''))
    except ValueError:
        raise GPUError('Invalid GPU service port.') from None
    if not (local or tunnel):
        raise GPUError('Use the notebook HTTPS trycloudflare.com URL, or http://127.0.0.1:8001 for a local official ACE-Step API.')
    if len(key) > 512 or any(ord(c) < 32 or ord(c) > 126 for c in key) or (tunnel and not key):
        raise GPUError('The public GPU tunnel requires its private connection key. Upload the notebook connection file.')
    return {'url': url, 'key': key}


def settings():
    url = os.getenv('LOCAL_MUSIC_URL', '').strip()
    if url:
        return validate(url, os.getenv('LOCAL_MUSIC_API_KEY', ''))
    if not CONFIG.exists():
        return None
    try:
        data = json.loads(CONFIG.read_text())
        return validate(data['url'], data['key'])
    except (OSError, ValueError, KeyError, TypeError):
        raise GPUError('The saved GPU configuration is invalid. Upload a fresh connection file in Connections.') from None


def parse_connection(text):
    if not isinstance(text, str) or len(text) > 8192:
        raise GPUError('Choose the small song-service.env file downloaded by the notebook.')
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or key.strip() not in ('LOCAL_MUSIC_URL', 'LOCAL_MUSIC_API_KEY'):
            raise GPUError('This is not a supported notebook connection file.')
        values[key.strip()] = value.strip().strip('"').strip("'")
    return validate(values.get('LOCAL_MUSIC_URL', ''), values.get('LOCAL_MUSIC_API_KEY', ''))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the private API key to another origin or redirect target.
        return None


def request(config, path, data=None, audio=False):
    headers = {'Authorization': 'Bearer ' + config['key']} if config['key'] else {}
    body = None
    if data is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(config['url'] + path, data=body, headers=headers)
    limit = 128_000_000 if audio else 1_000_000
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=60 if audio else 30) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise GPUError('The GPU returned an oversized response. Try a shorter song.')
        if audio:
            return raw
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get('code') != 200 or result.get('error'):
            raise GPUError('The GPU rejected this request. Check its notebook log; no song was fabricated.')
        return result.get('data')
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise GPUError('GPU connection rejected (HTTP 401/403). Refresh the notebook connection file; the cloud network policy must also allow the tunnel host.') from None
        raise GPUError('The GPU service is unavailable. Keep Colab open and upload a fresh connection file. No song was fabricated.') from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise GPUError('Cannot reach the GPU service. Keep the notebook running, refresh its connection file and allow its tunnel host in cloud network settings.') from None
    except (ValueError, UnicodeError):
        raise GPUError('The GPU returned an invalid API response. Check that this is the official ACE-Step service.') from None


def probe(config=None):
    config = config or settings()
    if not config:
        raise GPUError('No GPU connection is configured.')
    if request(config, '/query_result', {'task_id_list': []}) != []:
        raise GPUError('Unexpected GPU readiness response. Check the notebook and connection file.')
    return {'authenticated': True, 'liveAudioVerified': False, 'listeningVerified': False,
            'note': 'Authenticated API check passed; actual song generation and listening are still unverified.'}


def save(text):
    if os.getenv('LOCAL_MUSIC_URL', '').strip():
        raise GPUError('LOCAL_MUSIC_URL is set by the host. Update that host configuration before uploading another connection.')
    config = parse_connection(text)
    checked = probe(config)  # Failed checks leave the previous configuration intact.
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=CONFIG.parent, prefix='.music-service-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(config, f)
        os.chmod(name, 0o600)
        os.replace(name, CONFIG)
    finally:
        Path(name).unlink(missing_ok=True)
    return checked


def disconnect():
    if os.getenv('LOCAL_MUSIC_URL', '').strip():
        raise GPUError('The GPU connection is managed by LOCAL_MUSIC_URL on the host; remove it there to use the CPU engine.')
    CONFIG.unlink(missing_ok=True)


def render(native):
    config = settings()
    if not config:
        raise GPUError('Connect the GPU notebook first.')
    # Official API names differ from the C++ CLI; do not forward fictitious fields.
    payload = {'prompt': native['caption'], 'lyrics': native['lyrics'],
               'vocal_language': native['vocal_language'], 'bpm': native['bpm'],
               'audio_duration': native['duration'], 'key_scale': 'C Major', 'time_signature': '4',
               'task_type': 'text2music', 'audio_format': 'wav', 'batch_size': 1,
               'inference_steps': 8, 'thinking': False, 'use_cot_caption': False, 'use_cot_language': False}
    submitted = request(config, '/release_task', payload)
    task = submitted.get('task_id') if isinstance(submitted, dict) else None
    if not isinstance(task, str) or not 1 <= len(task) <= 200:
        raise GPUError('The GPU did not return a task ID. No audio was fabricated.')
    deadline = time.monotonic() + min(1800, max(30, int(os.getenv('FREE_MUSIC_TIMEOUT', '1800'))))
    while time.monotonic() < deadline:
        rows = request(config, '/query_result', {'task_id_list': [task]})
        if not isinstance(rows, list):
            raise GPUError('Invalid GPU task response. No audio was fabricated.')
        if rows:
            row = next((r for r in rows if isinstance(r, dict) and r.get('task_id') == task), None)
            if row is None:
                raise GPUError('The GPU returned a different task. No audio was attached.')
            if row.get('status') == 2:
                raise GPUError('The GPU could not generate the song. Inspect its notebook log for memory/model errors. No song was fabricated.')
            if row.get('status') == 1:
                try:
                    outputs = json.loads(row['result'])
                    output = outputs[0]
                    p = urllib.parse.urlparse(output['file'])
                    if p.path != '/v1/audio' or p.fragment:
                        raise ValueError('unexpected audio endpoint')
                    # Use only our configured origin, even if API returns an absolute URL.
                    audio = request(config, p.path + ('?' + p.query if p.query else ''), audio=True)
                    words = output.get('lyrics', '')
                    return audio, words[:16000] if isinstance(words, str) else ''
                except (ValueError, TypeError, KeyError, IndexError):
                    raise GPUError('The GPU did not return a usable audio location. No audio was fabricated.') from None
        time.sleep(2)
    raise GPUError('The GPU did not finish within the time limit. Check its notebook before retrying; no audio was fabricated.')
