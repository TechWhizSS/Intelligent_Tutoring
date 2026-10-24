"""Run one Calculus and one BEEE demo against a running server.

Default creates source-linked drafts. --generate-audio runs the free local AI
and downloads only actual generated audio. Never substitutes a fixture or TTS.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8000')
parser.add_argument('--generate-audio', '--live', dest='generate_audio', action='store_true')
parser.add_argument('--length', type=int, choices=[30,60,120,180,240], default=30)
parser.add_argument('--language', choices=['en', 'hi'], default='en')
parser.add_argument('--sap', default='submission-demo')
args = parser.parse_args()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, body=None):
    req = urllib.request.Request(args.url.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'})
    try:
        with opener.open(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        print(json.load(exc).get('error', f'HTTP {exc.code}'), file=sys.stderr)
        sys.exit(2)


request('/api/login', {'sap': args.sap, 'password': 'sample'})
out = Path('runtime/demo-output')
out.mkdir(parents=True, exist_ok=True)
for topic_id in ['calc-01', 'beee-01']:
    song = request('/api/lyrics', {'topic': topic_id, 'language': args.language, 'mode': 'free', 'settings': {'length': args.length}})
    (out / f'{topic_id}-{args.language}.lyrics.txt').write_text(song['lyrics'])
    print(f"{topic_id}: {song['provenance']}")
    questions = request(f'/api/topics/{topic_id}/quiz?language={args.language}')
    (out / f'{topic_id}-{args.language}.quiz.json').write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    if not args.generate_audio:
        print('  No audio generated. Run --generate-audio after installing the free model files. No paid API is used.')
        continue
    request(f"/api/songs/{song['id']}/synthesize", {})
    deadline = time.time() + 1860
    while time.time() < deadline:
        time.sleep(3)
        current = next(s for s in request('/api/songs') if s['id'] == song['id'])
        if current['status'] == 'failed':
            print(current['error'], file=sys.stderr)
            sys.exit(2)
        if current['status'] == 'ready':
            with opener.open(args.url.rstrip('/') + current['audioUrl']) as response:
                path = out / f"{topic_id}-{args.language}{'.wav' if 'wav' in current['mime'] else '.mp3'}"
                path.write_bytes(response.read())
            print(f'  Real returned audio: {path}')
            break
    else:
        print('Generation still pending. Check the song library.', file=sys.stderr)
        sys.exit(2)
print('Demo records are saved. Sign in with the same SAP ID to open them in the website.')
