"""Capture actual current website screens using isolated sample data and no audio fixtures."""
from pathlib import Path
import os,shutil,socket,subprocess,sys,tempfile,time,urllib.request
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/report/screenshots'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env={**os.environ,'APP_DATA_DIR':temp,'HOST':'127.0.0.1','PORT':str(port),'FREE_MUSIC_HOME':str(Path(temp)/'no-models')}
        server=subprocess.Popen([sys.executable,'-m','app.server'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            url=f'http://127.0.0.1:{port}'
            for _ in range(80):
                try:urllib.request.urlopen(url+'/api/health',timeout=1).close();break
                except OSError:time.sleep(.1)
            with sync_playwright() as p:
                executable=shutil.which('chromium')
                browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
                page.goto(url);page.locator('#login-form').wait_for();page.screenshot(path=str(OUT/'web-login.png'))
                page.get_by_role('button',name='Try the sample student account').click()
                page.get_by_role('heading',name='Your learning, on repeat.').wait_for()
                page.screenshot(path=str(OUT/'web-studio.png'))
                page.locator('#subject').select_option('beee')
                page.get_by_role('button',name='Generate lyrics',exact=True).click();page.locator('#lyrics').wait_for()
                page.locator('#toast.visible').wait_for(state='hidden')
                page.locator('.provider-workspace').screenshot(path=str(OUT/'web-gemini.png'))
                page.get_by_role('button',name='Chapter notes',exact=True).click();page.locator('.note-item').first.wait_for()
                page.screenshot(path=str(OUT/'web-notes.png'))
                page.get_by_role('button',name='Practice quiz',exact=True).click();page.locator('#quiz-form').wait_for()
                page.locator('input[name=q0]').first.check();page.locator('input[name=q1]').first.check()
                page.get_by_role('button',name='Check my answers',exact=True).click();page.locator('.feedback').wait_for()
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(OUT/'web-quiz.png'))
                page.get_by_role('button',name='Syllabus report').click();page.locator('#coverage-rows tr').first.wait_for()
                assert page.locator('#coverage-rows tr').count()==91
                page.screenshot(path=str(OUT/'web-coverage.png'))
                page.get_by_role('button',name='Song library',exact=True).click();page.locator('.song-card').first.wait_for()
                page.screenshot(path=str(OUT/'web-library.png'))
                page.get_by_role('button',name='Song studio',exact=True).click()
                page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(OUT/'web-mobile.png'))
                browser.close()
            print('Captured current sunrise website UI with sample drafts only; no generated or fixture audio.')
        finally:server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
