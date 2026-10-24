"""Dependency-free full-stack demo: Python HTTP API + SQLite + browser client."""
import base64
import concurrent.futures
import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

from . import content, providers, store

ROOT = content.ROOT
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
RATE_LOCK = threading.Lock()
RATE = {}
PROVIDER_CHECK = None


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def limited(key, limit, seconds):
    with RATE_LOCK:
        now = time.time()
        values = [v for v in RATE.get(key, []) if v > now - seconds]
        if len(values) >= limit:
            raise APIError(429, 'Too many requests. Please wait before trying again.')
        RATE[key] = values + [now]


def topic_by_id(value):
    if value not in content.TOPICS:
        raise APIError(404, 'Topic not found in the uploaded syllabus.')
    return content.TOPICS[value]


def settings_from(body):
    options = {
        'genre': ['Pop', 'Lo-fi', 'Hip-hop', 'Acoustic', 'Electronic', 'Indian fusion', 'Rock'],
        'mood': ['Uplifting', 'Calm', 'Energetic', 'Focused'],
        'vocal': ['Warm', 'Bright', 'Low register', 'High register', 'Duet', 'Female vocal', 'Male vocal'],
        'difficulty': ['Beginner', 'Intermediate', 'Exam revision'],
    }
    result = {}
    supplied = body.get('settings', {})
    if not isinstance(supplied, dict):
        raise APIError(400, 'Settings must be an object.')
    for key, choices in options.items():
        result[key] = supplied.get(key, choices[0])
        if result[key] not in choices:
            raise APIError(400, f'Unsupported {key}.')
    for key, default, low, high in [('tempo', 100, 60, 180), ('length', 30, 30, 240), ('formulaRepeats', 2, 1, 4)]:
        try:
            result[key] = int(supplied.get(key, default))
        except (ValueError, TypeError):
            raise APIError(400, f'Invalid {key}.')
        if not low <= result[key] <= high:
            raise APIError(400, f'{key} must be between {low} and {high}.')
    result['instructions'] = str(supplied.get('instructions', ''))[:1500]
    return result


def public_song(row):
    row = dict(row)
    row['settings'] = json.loads(row['settings'])
    row['audioUrl'] = f"/api/songs/{row['id']}/audio" if row['audio'] else None
    del row['audio']
    del row['sap']
    return row


def seed_sample(sap):
    """Four explicitly labelled drafts for the 'Try sample' account; never fake audio."""
    if sap != '70572400001' or store.rows('SELECT id FROM songs WHERE sap=? LIMIT 1', (sap,)):
        return
    for topic_id in ['calc-01', 'beee-01']:
        topic = content.TOPICS[topic_id]
        for language in ['en', 'hi']:
            store.execute('INSERT INTO songs (id,sap,topic,language,title,lyrics,settings,provenance,status,source_hash,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                          (str(uuid.uuid4()), sap, topic_id, language, topic['title'], content.demo_lyrics(topic, language),
                           json.dumps(settings_from({})), 'Offline template; supplemental; no audio', 'draft', content.source_hash(topic), time.time()))


def synthesize(song):
    try:
        audio, mime, provider_lyrics = providers.music(song['lyrics'], content.LANGUAGES[song['language']], json.loads(song['settings']))
        name = song['id'] + ('.wav' if 'wav' in mime else '.mp3')
        (store.RUNTIME / name).write_bytes(audio)
        store.execute("UPDATE songs SET status='ready', audio=?, mime=?, error=NULL, provider_lyrics=?,audio_origin=? WHERE id=?",
                      (name, mime, provider_lyrics, providers.MUSIC_PROVIDER_NAME, song['id']))
    except Exception as exc:
        message = str(exc) if isinstance(exc, providers.ProviderError) else 'Synthesis failed. No audio was created. Please retry.'
        store.execute("UPDATE songs SET status='failed', error=?,audio=NULL,mime=NULL,audio_origin=NULL WHERE id=?", (message, song['id']))


class Handler(BaseHTTPRequestHandler):
    server_version = 'SyllabusToSong/1.0'

    def log_message(self, format, *args):
        # Avoid logging request bodies, cookies, API keys, SAP IDs or query strings.
        pass

    def headers_for(self, status, mime, length, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(length))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def send(self, value, status=200, extra=None):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.headers_for(status, 'application/json; charset=utf-8', len(data), extra)
        self.wfile.write(data)

    def body(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise APIError(400, 'Invalid content length.')
        if length < 0 or length > 22_000_000:
            raise APIError(413, 'Upload too large (16 MB decoded maximum).')
        try:
            result = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise APIError(400, 'A valid JSON request body is required.')
        if not isinstance(result, dict):
            raise APIError(400, 'A JSON object is required.')
        return result

    def session(self, admin=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['session'].value
        except (KeyError, ValueError):
            raise APIError(401, 'Please sign in with your SAP ID.')
        result = store.rows('SELECT * FROM sessions WHERE token=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time()))
        if not result:
            raise APIError(401, 'Session expired. Please sign in again.')
        session = result[0]
        if admin and session['role'] != 'admin':
            raise APIError(403, 'Administrator login required.')
        return session

    def dispatch(self, method):
        try:
            path = unquote(urlparse(self.path).path)
            if method == 'GET':
                self.get(path)
            else:
                origin = self.headers.get('Origin')
                if origin:
                    parsed = urlparse(origin)
                    if parsed.netloc != self.headers.get('Host') or parsed.scheme not in ('http', 'https'):
                        raise APIError(403, 'Cross-origin requests are not allowed.')
                if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    raise APIError(403, 'Cross-site requests are not allowed.')
                self.post(path, self.body())
        except APIError as exc:
            self.send({'error': exc.message}, exc.status)
        except providers.ProviderError as exc:
            self.send({'error': str(exc), 'mode': 'demo'}, 503)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send({'error': 'An unexpected server error occurred. Please retry.'}, 500)

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def get(self, path):
        if path == '/api/health':
            return self.send({'ok': True, 'name': 'Syllabus to Song'})
        if path == '/api/me':
            session = self.session()
            return self.send({'sap': session['sap'], 'role': session['role']})
        if path == '/api/catalogue':
            self.session()
            return self.send(content.CATALOGUE)
        if path == '/api/providers':
            self.session()
            return self.send({'configured': providers.configured(), 'mode': 'free local AI ready' if providers.configured() else 'free model setup required',
                              'lyricsModel': providers.LYRICS_MODEL, 'musicModel': providers.MUSIC_MODEL,
                              'check': PROVIDER_CHECK, 'liveAudioVerified': bool(store.rows("SELECT id FROM songs WHERE status='ready' AND audio_origin=? LIMIT 1", (providers.MUSIC_PROVIDER_NAME,))),
                              'blocker': providers.blocker(),
                              'capabilities': 'ACE-Step accepts native BPM, duration and vocal language fields plus exact edited lyrics. Genre, mood, voice and repetition guide the caption. No payment or API key; CPU generation can be slow. Singing quality and Hindi pronunciation require review.'})
        if path == '/api/songs':
            session = self.session()
            return self.send([public_song(s) for s in store.rows('SELECT * FROM songs WHERE sap=? ORDER BY created DESC', (session['sap'],))])
        if path == '/api/attempts':
            session = self.session()
            return self.send(store.rows('SELECT topic,score,total,created FROM attempts WHERE sap=? ORDER BY created DESC', (session['sap'],)))
        if path.startswith('/api/topics/'):
            self.session()
            segments = path.split('/')
            topic = topic_by_id(segments[3])
            lang = parse_qs(urlparse(self.path).query).get('language', ['en'])[0]
            if lang not in content.LANGUAGES:
                raise APIError(400, 'Only English and Hindi are supported.')
            if len(segments) == 5 and segments[4] == 'quiz':
                return self.send({'questions': content.quiz(topic, lang), 'provenance': 'Supplemental source-derived revision quiz; not an official examination'})
            if len(segments) != 4:
                raise APIError(404, 'Route not found.')
            uploads = store.rows('SELECT id,name,excerpt,approved FROM uploads WHERE topic=? AND approved=1', (topic['id'],))
            return self.send({**topic, 'supplemental': content.supplemental(topic), 'uploads': uploads})
        if path in ('/api/coverage', '/api/coverage.csv'):
            session = self.session()
            songs = store.rows('SELECT topic,language,status FROM songs WHERE sap=?', (session['sap'],))
            report = []
            for topic in content.TOPICS.values():
                entries = [s for s in songs if s['topic'] == topic['id']]
                report.append(dict(id=topic['id'], subject=topic['subject'], unit=topic['unit'], chapter=topic['chapter'], topic=topic['title'],
                                   content='Uploaded summary; full notes pending', hindi='Supplemental explanation available',
                                   lyrics_en='Saved draft' if any(s['language'] == 'en' for s in entries) else 'Offline template available; not saved',
                                   lyrics_hi='Saved draft' if any(s['language'] == 'hi' for s in entries) else 'Offline template available; not saved',
                                   quiz='2 supplemental revision questions ready',
                                   audio='Ready' if any(s['status'] == 'ready' for s in entries) else 'Not generated', source=topic['source'], locator=topic['locator']))
            if path.endswith('.csv'):
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=list(report[0]))
                writer.writeheader()
                writer.writerows(report)
                data = ('\ufeff' + buf.getvalue()).encode()
                self.headers_for(200, 'text/csv; charset=utf-8', len(data), {'Content-Disposition': 'attachment; filename="syllabus-completeness.csv"'})
                return self.wfile.write(data)
            return self.send({'topics': report, 'indexed': len(report), 'fullNotesReady': 0,
                              'note': 'All uploaded headings are indexed. Audio readiness and full notes are tracked separately.'})
        if path == '/api/admin/uploads':
            self.session(admin=True)
            return self.send(store.rows('SELECT id,topic,name,excerpt,approved,created FROM uploads ORDER BY created DESC'))
        if path.startswith('/api/sources/'):
            self.session()
            filename = path.removeprefix('/api/sources/')
            if filename not in [s['file'] for s in content.CATALOGUE['sources']]:
                raise APIError(404, 'Source not found.')
            return self.file(ROOT / 'sources' / filename, download=True)
        match = re.fullmatch(r'/api/songs/([a-f0-9-]+)/audio', path)
        if match:
            session = self.session()
            found = store.rows('SELECT * FROM songs WHERE id=? AND sap=?', (match[1], session['sap']))
            if not found or not found[0]['audio']:
                raise APIError(404, 'No audio exists for this song.')
            return self.file(store.RUNTIME / found[0]['audio'], found[0]['mime'], 'download' in parse_qs(urlparse(self.path).query))
        static = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
        if path not in static:
            raise APIError(404, 'Page not found.')
        self.file(ROOT / 'static' / static[path])

    def file(self, path, mime=None, download=False):
        if not path.is_file():
            raise APIError(404, 'File not found.')
        data = path.read_bytes()
        mime = mime or mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        extra = {'Accept-Ranges': 'bytes'}
        if download:
            extra['Content-Disposition'] = f'attachment; filename="{re.sub(r"[^a-zA-Z0-9._-]", "_", path.name)}"'
        status = 200
        if self.headers.get('Range'):
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers['Range'])
            if not match or not any(match.groups()):
                raise APIError(416, 'Unsupported byte range.')
            size = len(data)
            start = int(match[1]) if match[1] else max(0, size - int(match[2]))
            end = min(int(match[2]), size - 1) if match[1] and match[2] else size - 1
            if start >= size or start > end:
                raise APIError(416, 'Byte range outside file.')
            data = data[start:end + 1]
            status = 206
            extra['Content-Range'] = f'bytes {start}-{end}/{size}'
        self.headers_for(status, mime, len(data), extra)
        self.wfile.write(data)

    def post(self, path, body):
        global PROVIDER_CHECK
        if path == '/api/login':
            limited(('login', self.client_address[0]), 40, 60)
            sap = str(body.get('sap', '')).strip()
            password = str(body.get('password', ''))
            if not re.fullmatch(r'[a-zA-Z0-9_-]{3,30}', sap) or not password or len(password) > 200:
                raise APIError(400, 'Enter a SAP ID (3–30 letters or digits) and any nonempty sample password.')
            role = 'student'
            if sap == os.getenv('ADMIN_SAP_ID', 'admin'):
                if not hmac.compare_digest(password.encode(), os.getenv('ADMIN_PASSWORD', 'demo-admin').encode()):
                    raise APIError(401, 'Incorrect administrator password.')
                role = 'admin'
            token = secrets.token_urlsafe(32)
            store.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            store.execute('INSERT INTO sessions VALUES(?,?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), sap, role, time.time() + 86400))
            seed_sample(sap)
            cookie = f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'
            if os.getenv('COOKIE_SECURE') == '1':
                cookie += '; Secure'
            return self.send({'sap': sap, 'role': role, 'sampleLogin': True}, extra={'Set-Cookie': cookie})
        session = self.session()
        if path == '/api/logout':
            store.execute('DELETE FROM sessions WHERE token=?', (session['token'],))
            return self.send({'ok': True}, extra={'Set-Cookie': 'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        if path == '/api/providers/check':
            self.session(admin=True)
            limited(('provider-check', session['sap']), 3, 60)
            PROVIDER_CHECK = providers.check()
            return self.send(PROVIDER_CHECK)
        if path == '/api/lyrics':
            limited(('lyrics', session['sap']), 30, 3600)
            topic = topic_by_id(body.get('topic'))
            language = body.get('language', 'en')
            if language not in content.LANGUAGES:
                raise APIError(400, 'Only English and Hindi are supported.')
            settings = settings_from(body)
            mode = body.get('mode', 'free')
            if mode not in ('demo', 'live', 'free'):
                raise APIError(400, 'Choose free source-linked drafting or the offline template.')
            approved = store.rows('SELECT name,excerpt FROM uploads WHERE topic=? AND approved=1', (topic['id'],))
            result = providers.lyrics(topic, content.LANGUAGES[language], settings, approved) if mode in ('live', 'free') else content.demo_lyrics(topic, language)
            provenance = 'Local source-linked template; supplemental; no LLM' if mode in ('live', 'free') else 'Offline template; supplemental; no audio'
            song_id = str(uuid.uuid4())
            store.execute('INSERT INTO songs (id,sap,topic,language,title,lyrics,settings,provenance,status,audio,mime,error,provider_lyrics,source_hash,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (song_id, session['sap'], topic['id'], language, topic['title'], result, json.dumps(settings), provenance,
                           'draft', None, None, None, None, content.source_hash(topic), time.time()))
            return self.send(public_song(store.rows('SELECT * FROM songs WHERE id=?', (song_id,))[0]), 201)
        match = re.fullmatch(r'/api/songs/([a-f0-9-]+)/(save|synthesize|upload-audio)', path)
        if match:
            found = store.rows('SELECT * FROM songs WHERE id=? AND sap=?', (match[1], session['sap']))
            if not found:
                raise APIError(404, 'Song not found.')
            song = found[0]
            action = match[2]
            if song['status'] == 'generating':
                raise APIError(409, 'This song is already generating. Wait for it to finish.')
            if action == 'save':
                text = body.get('lyrics')
                if not isinstance(text, str) or not 1 <= len(text.strip()) <= 16000:
                    raise APIError(400, 'Lyrics must contain 1–16000 characters.')
                settings = settings_from(body) if 'settings' in body else json.loads(song['settings'])
                # Audio remains attached to its exact lyric revision. Edited drafts require fresh synthesis.
                if text != song['lyrics'] or settings != json.loads(song['settings']):
                    store.execute("UPDATE songs SET lyrics=?,settings=?,status='draft',audio=NULL,mime=NULL,provider_lyrics=NULL,audio_origin=NULL,error=NULL WHERE id=?", (text, json.dumps(settings), song['id']))
            elif action == 'synthesize':
                limited(('synthesize', session['sap']), 10, 3600)
                if not providers.configured():
                    raise providers.ProviderError(providers.blocker())
                # Serialize expensive inference to avoid exhausting RAM on a small free host.
                with store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if db.execute("SELECT id FROM songs WHERE status='generating' LIMIT 1").fetchone():
                        raise APIError(409, 'The free music engine is busy with another song. Try again after it finishes.')
                    if db.execute("UPDATE songs SET status='generating',error=NULL WHERE id=? AND status!='generating'", (song['id'],)).rowcount != 1:
                        raise APIError(409, 'Song already generating.')
                POOL.submit(synthesize, song)
            elif action == 'upload-audio':
                data, mime = self.decode_audio(body)
                filename = song['id'] + ('.wav' if 'wav' in mime else '.mp3')
                (store.RUNTIME / filename).write_bytes(data)
                store.execute("UPDATE songs SET status='ready',audio=?,mime=?,audio_origin='User supplied audio; not generated by this app',error=NULL WHERE id=?", (filename, mime, song['id']))
            return self.send(public_song(store.rows('SELECT * FROM songs WHERE id=?', (song['id'],))[0]))
        if path == '/api/quiz/submit':
            topic = topic_by_id(body.get('topic'))
            language = body.get('language', 'en')
            if language not in content.LANGUAGES:
                raise APIError(400, 'Only English and Hindi are supported.')
            questions = content.quiz(topic, language, answers=True)
            answers = body.get('answers')
            if not isinstance(answers, list) or len(answers) != len(questions) or any(type(a) is not int or not 0 <= a < 4 for a in answers):
                raise APIError(400, 'Answer every question before submitting.')
            score = sum(a == q['correct'] for a, q in zip(answers, questions))
            store.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), session['sap'], topic['id'], score, len(questions), time.time()))
            return self.send({'score': score, 'total': len(questions), 'feedback': questions})
        if path == '/api/admin/uploads':
            self.session(admin=True)
            topic_by_id(body.get('topic'))
            name, excerpt = str(body.get('name', '')).strip(), str(body.get('excerpt', '')).strip()
            if not 1 <= len(name) <= 150 or not 10 <= len(excerpt) <= 30000:
                raise APIError(400, 'Enter a source name and a 10–30000 character academic excerpt.')
            filename = None
            if body.get('data'):
                try:
                    data = base64.b64decode(body['data'], validate=True)
                except (ValueError, TypeError):
                    raise APIError(400, 'Invalid upload encoding.')
                if len(data) > 16_000_000:
                    raise APIError(413, 'Maximum upload size is 16 MB.')
                extension = Path(name).suffix.lower()
                if extension not in ('.pdf', '.txt', '.md', '.csv'):
                    raise APIError(400, 'Upload PDF, TXT, MD or CSV material.')
                filename = str(uuid.uuid4()) + extension
                (store.RUNTIME / filename).write_bytes(data)
            uid = str(uuid.uuid4())
            store.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?,?)', (uid, body['topic'], name, excerpt, filename, 0, time.time()))
            return self.send({'id': uid, 'approved': False, 'note': 'Pending admin review; becomes supplemental chapter material after approval.'}, 201)
        match = re.fullmatch(r'/api/admin/uploads/([a-f0-9-]+)/approve', path)
        if match:
            self.session(admin=True)
            if not store.rows('SELECT id FROM uploads WHERE id=?', (match[1],)):
                raise APIError(404, 'Upload not found.')
            store.execute('UPDATE uploads SET approved=1 WHERE id=?', (match[1],))
            return self.send({'approved': True, 'label': 'Admin-approved supplemental material; not an official syllabus change'})
        raise APIError(404, 'API route not found.')

    def decode_audio(self, body):
        if body.get('permitted') is not True:
            raise APIError(400, 'Confirm you have permission to use and download this audio.')
        mime = body.get('mime')
        try:
            data = base64.b64decode(body.get('data', ''), validate=True)
        except (ValueError, TypeError):
            raise APIError(400, 'Invalid audio encoding.')
        if not 40 <= len(data) <= 16_000_000:
            raise APIError(400, 'Audio must be between 40 bytes and 16 MB.')
        if mime in ('audio/wav', 'audio/x-wav', 'audio/wave') and data[:4] == b'RIFF' and data[8:12] == b'WAVE':
            return data, 'audio/wav'
        if mime in ('audio/mpeg', 'audio/mp3') and (data[:3] == b'ID3' or data[:1] == b'\xff'):
            return data, 'audio/mpeg'
        raise APIError(400, 'Use a valid WAV or MP3 audio file.')


def main():
    store.init()
    host, port = os.getenv('HOST', '0.0.0.0'), int(os.getenv('PORT', '8000'))
    print(f'Syllabus to Song running on http://{host}:{port}', flush=True)
    print('Sample student login accepts any nonempty password. No real student data should be stored.', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    main()
