"""Build the free CPU music engine and download its public quantized model weights.

No payment, provider key or hosted inference account is used. A one-time network
connection to GitHub and Hugging Face is needed. Afterwards inference is offline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HOME_DIR = Path(os.getenv('FREE_MUSIC_HOME', ROOT / 'runtime/free-music')).resolve()
SOURCE = HOME_DIR / 'acestep.cpp'
MODELS = HOME_DIR / 'models'
REVISION = 'de858d8e1a94f0e1939cf9bdd8ff7d9631953077'
REPO = 'https://github.com/ServeurpersoCom/acestep.cpp.git'
MODEL_REPO = 'Serveurperso/ACE-Step-1.5-GGUF'
FILES = ['acestep-v15-turbo-Q4_K_M.gguf', 'Qwen3-Embedding-0.6B-Q8_0.gguf', 'vae-BF16.gguf']


def run(args):
    subprocess.run(args, check=True)


def build():
    if not shutil.which('git') or not shutil.which('g++'):
        raise RuntimeError('Install git and a C++17 compiler (g++) before building the free engine.')
    if not SOURCE.exists():
        run(['git', 'clone', REPO, str(SOURCE)])
    run(['git', '-C', str(SOURCE), 'checkout', '--detach', REVISION])
    run(['git', '-C', str(SOURCE), 'submodule', 'update', '--init', '--recursive', '--depth', '1'])
    cmake = shutil.which('cmake')
    if not cmake:
        tools = HOME_DIR / 'build-tools'
        run([sys.executable, '-m', 'pip', 'install', '--target', str(tools), 'cmake==4.4.4'])
        cmake = str(tools / 'cmake/data/bin/cmake')
    run([cmake, '-S', str(SOURCE), '-B', str(SOURCE / 'build'), '-DCMAKE_BUILD_TYPE=Release',
         '-DGGML_BLAS=OFF', '-DGGML_CUDA=OFF', '-DGGML_METAL=OFF'])
    run([cmake, '--build', str(SOURCE / 'build'), '--target', 'ace-synth', '-j', '2'])
    print('Free CPU engine compiled. No music is claimed until inference produces audio.', flush=True)


def download_models():
    MODELS.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen('https://huggingface.co/api/models/' + MODEL_REPO + '?blobs=true', timeout=30) as response:
        metadata = json.load(response)
    revision = metadata['sha']
    if not isinstance(revision, str) or len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise RuntimeError('Invalid model repository revision returned by the model host.')
    siblings = {s['rfilename']: s for s in metadata['siblings']}
    manifest = {'source': MODEL_REPO, 'revision': revision, 'engineRevision': REVISION, 'files': []}
    for name in FILES:
        info = siblings.get(name, {})
        expected = info.get('lfs', {}).get('sha256') or info.get('lfs', {}).get('oid')
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise RuntimeError('Public LFS checksum unavailable for ' + name + '; refusing an unverified model download.')
        target = MODELS / name
        if target.exists():
            with target.open('rb') as file:
                digest = hashlib.file_digest(file, 'sha256').hexdigest()
            if digest == expected:
                print('Verified cached model: ' + name, flush=True)
                manifest['files'].append({'file': name, 'sha256': digest, 'bytes': target.stat().st_size})
                continue
        partial = target.with_suffix(target.suffix + '.part')
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {'Range': f'bytes={offset}-'} if offset else {}
        req = urllib.request.Request(f'https://huggingface.co/{MODEL_REPO}/resolve/{revision}/{name}', headers=headers)
        print('Downloading free model: ' + name, flush=True)
        with urllib.request.urlopen(req, timeout=60) as response:
            resume = offset > 0 and response.status == 206
            count = offset if resume else 0
            with partial.open('ab' if resume else 'wb') as file:
                while chunk := response.read(1024 * 1024):
                    file.write(chunk)
                    count += len(chunk)
                    if count // (64 * 1024 * 1024) != (count - len(chunk)) // (64 * 1024 * 1024):
                        print(f'  {name}: {count // (1024 * 1024)} MiB', flush=True)
        with partial.open('rb') as file:
            digest = hashlib.file_digest(file, 'sha256').hexdigest()
        if digest != expected:
            raise RuntimeError('Checksum mismatch for ' + name + '. Remove the .part file and retry.')
        with partial.open('rb') as file:
            if file.read(4) != b'GGUF':
                raise RuntimeError('Model is not a GGUF file: ' + name)
        partial.replace(target)
        manifest['files'].append({'file': name, 'sha256': digest, 'bytes': target.stat().st_size})
    (MODELS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('All free model files downloaded and checksum verified. Start the website and synthesize a 30-second song.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--models-only', action='store_true')
    args = parser.parse_args()
    if args.build_only and args.models_only:
        parser.error('Choose only one setup phase or neither for both.')
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if not args.models_only:
            build()
        if not args.build_only:
            download_models()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('FREE MUSIC SETUP BLOCKED: ' + str(exc), file=sys.stderr)
        print('If the proxy reports 403, enable Hugging Face access in the cloud network settings. Model downloads may also need *.hf.co (including Xet/CDN hosts). No payment or paid fallback is required.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
