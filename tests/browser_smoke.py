"""Isolated browser checks. A test-only silent WAV verifies playback, never song generation."""
import io
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'test-results'
OUTPUT.mkdir(exist_ok=True)


def wait_js(page, expression):
    # Evaluate through browser automation, avoiding string eval under the app CSP.
    for _ in range(200):
        if page.evaluate(expression):
            return
        time.sleep(.05)
    raise AssertionError('Browser condition timed out: ' + expression)


def main():
    with tempfile.TemporaryDirectory() as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = {**os.environ, 'APP_DATA_DIR': temp, 'HOST': '127.0.0.1', 'PORT': str(port),
               'FREE_MUSIC_HOME': str(Path(temp)/'missing-models'), 'ADMIN_SAP_ID': 'admin', 'ADMIN_PASSWORD': 'demo-admin'}
        server = subprocess.Popen([sys.executable, '-m', 'app.server'], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f'http://127.0.0.1:{port}'
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(url + '/api/health', timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Temporary server did not start')
            with sync_playwright() as p:
                chromium = os.getenv('CHROMIUM_PATH') or shutil.which('chromium')
                browser = p.chromium.launch(**({'executable_path': chromium} if chromium else {}), headless=True,
                                            args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1080})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                page.screenshot(path=str(OUTPUT / 'login-desktop.png'), full_page=True)
                page.get_by_role('button', name='Try the sample student account').click()
                page.get_by_role('heading', name='Your learning, on repeat.').wait_for()
                assert page.locator('#song-select option').count() == 3, 'English and Hindi example drafts should be available'
                # Verify our embedding controls, not Google's willingness to be embedded.
                page.route('https://gemini.google.com/**',lambda route:route.abort())
                page.get_by_role('button',name='Try Gemini inside this page',exact=True).click()
                assert page.get_by_title('Gemini external website preview').get_attribute('src')=='https://gemini.google.com'
                page.get_by_role('button',name='Close preview',exact=True).click()
                assert page.locator('#external-music-preview iframe').count()==0
                for subject in ['calculus', 'beee']:
                    page.locator('#subject').select_option(subject)
                    for language in ['en', 'hi']:
                        page.locator('#language').select_option(language)
                        page.get_by_role('button', name='Generate lyrics', exact=True).click()
                        page.locator('#lyrics').wait_for()
                        original = page.locator('#lyrics').input_value()
                        assert '[Chorus]' in original
                        if language == 'hi':
                            assert 'समझो' in original
                        page.locator('#lyrics').fill(original + '\nReviewed for demo')
                        page.get_by_role('button', name='Save lyrics', exact=True).click()
                        wait_js(page, "document.querySelector('#toast').textContent === 'Lyrics saved.'")
                        assert page.get_by_role('link', name='Open Gemini / sign in ↗').get_attribute('href') == 'https://gemini.google.com'
                        assert page.get_by_role('button',name='Copy prompt for Gemini',exact=True).count()==1
                        assert page.locator('#audio-player').count() == 0
                with page.expect_download() as exported:
                    page.get_by_role('button', name='Export song prompt', exact=True).click()
                assert exported.value.suggested_filename.endswith('-song-prompt.txt')
                page.locator('#toast').evaluate("e=>{e.textContent='';e.className='';}")
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(OUTPUT / 'studio-desktop.png'), full_page=True)
                page.get_by_role('button', name='Practice quiz', exact=True).click()
                page.locator('#quiz-form').wait_for()
                page.locator('input[name=q0]').first.check()
                page.locator('input[name=q1]').first.check()
                page.get_by_role('button', name='Check my answers').click()
                page.locator('.feedback').wait_for()
                page.get_by_role('button', name='Syllabus report').click()
                page.locator('#coverage-rows tr').first.wait_for()
                assert page.locator('#coverage-rows tr').count() == 91
                with page.expect_download() as download:
                    page.get_by_role('link', name='Download report').click()
                assert download.value.suggested_filename == 'syllabus-completeness.csv'
                page.get_by_role('button', name='Chapter notes', exact=True).click()
                page.locator('.note-item').first.wait_for()
                assert page.locator('.note-item').count() == 11
                page.get_by_role('button', name='Song studio', exact=True).click()
                page.locator('#song-select').select_option(index=1)
                page.get_by_text('Attach your own permitted audio', exact=True).click()
                buffer = io.BytesIO()
                with wave.open(buffer, 'wb') as wav:
                    wav.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                    wav.writeframes(b'\0\0' * 16000)
                # Test-only silent audio. Never checked in or seeded into the actual application.
                page.locator('#audio-file').set_input_files({'name': 'test-only-silence.wav', 'mimeType': 'audio/wav', 'buffer': buffer.getvalue()})
                page.locator('#audio-permitted').check()
                page.get_by_role('button', name='Attach audio', exact=True).click()
                page.locator('#audio-player').wait_for()
                wait_js(page, "document.querySelector('audio').duration > 0")
                page.evaluate("window.testPlayer=document.querySelector('audio');window.testPlayer.play()")
                wait_js(page, "!document.querySelector('audio').paused")
                page.evaluate("document.querySelector('audio').currentTime = 0.5")
                assert page.evaluate("document.querySelector('audio').currentTime >= 0.5")
                page.get_by_role('button', name='Song library', exact=True).click()
                assert page.evaluate("window.testPlayer===document.querySelector('audio')"), 'Navigation must preserve the player'
                assert page.locator('.song-card').count() >= 8
                with page.expect_download() as download:
                    page.get_by_role('link', name='Download', exact=True).click()
                assert download.value.suggested_filename.endswith('.wav')
                page.get_by_role('button', name='Song studio', exact=True).click()
                for width in [390, 768]:
                    page.set_viewport_size({'width': width, 'height': 844})
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(OUTPUT / f'studio-{width}.png'), full_page=True)
                    overflow=page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>window.innerWidth+1 && getComputedStyle(e).position!=='fixed' && !e.closest('.nav')).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).slice(0,40)""")
                    assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth'), f'Mobile overflow at {width}px, document width {page.evaluate("document.documentElement.scrollWidth")}: {overflow}'
                page.get_by_role('button', name='Sign out', exact=True).click()
                page.locator('#sap').fill('admin')
                page.locator('#password').fill('demo-admin')
                page.locator('#login-form button[type=submit]').click()
                page.get_by_role('button', name='Admin uploads', exact=True).click()
                page.locator('#upload-name').fill('Review example.txt')
                page.locator('#upload-excerpt').fill('Academic excerpt: resistance relates voltage to current. <script>alert(1)</script>')
                page.get_by_role('button', name='Upload for review', exact=True).click()
                page.get_by_role('button', name='Approve reviewed excerpt', exact=True).wait_for()
                page.get_by_role('button', name='Approve reviewed excerpt', exact=True).click()
                page.get_by_text('Admin-approved supplemental material', exact=True).wait_for()
                page.get_by_role('button', name='Connections', exact=True).click()
                page.locator('#gpu-form').wait_for()
                assert page.get_by_role('link',name='free Colab singing notebook ↗').count()==1
                # An invalid connection file is rejected as data before any network call.
                page.locator('#gpu-file').set_input_files({'name':'song-service.env','mimeType':'text/plain','buffer':b'NOT_A_CONNECTION=do-not-execute'})
                page.get_by_role('button',name='Connect and test GPU',exact=True).click()
                wait_js(page,"document.querySelector('#toast').textContent.includes('not a supported notebook connection file')")
                assert page.locator('#gpu-file').input_value()!=''
                page.get_by_role('button',name='Use local CPU engine',exact=True).click()
                wait_js(page,"document.querySelector('#toast').textContent === 'Local CPU engine selected.'")
                page.get_by_role('button', name='Check free engine setup', exact=True).click()
                wait_js(page, "document.querySelector('#provider-result').textContent.includes('model weights not downloaded')")
                assert errors == [], errors
                browser.close()
            print('PASS: bilingual flows for both subjects, save, Gemini handoff/preview controls, notes, quizzes, all 91 report rows, CSV/audio downloads, real browser playback, uninterrupted navigation, mobile/tablet layout, admin review, credential check, no JavaScript errors.')
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == '__main__':
    main()
