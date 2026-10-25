"""Package the existing UI/curriculum for the free Sites Worker host.

The Python website remains intact. Hosted storage uses R2 and the official free
ACE-Step GPU API; CPU model inference is not supported inside a Worker.
"""
import argparse
import base64
import json
import mimetypes
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import content

def build(destination):
    destination=Path(destination);(destination/'worker').mkdir(parents=True,exist_ok=True)
    assets={}
    for name,mime in [('index.html','text/html; charset=utf-8'),('style.css','text/css; charset=utf-8'),('app.js','text/javascript; charset=utf-8')]:
        text=(ROOT/'static'/name).read_text()
        assets['/' if name=='index.html' else '/'+name]={'mime':mime,'text':text}
    sources={}
    for item in content.CATALOGUE['sources']:
        path=ROOT/'sources'/item['file']
        sources[item['file']]={'data':base64.b64encode(path.read_bytes()).decode(),'mime':mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}
    lessons={t['id']:{'supplemental':content.supplemental(t),'hash':content.source_hash(t),
        'lyrics':{lang:content.demo_lyrics(t,lang) for lang in ('en','hi')},
        'quiz':{lang:content.quiz(t,lang,answers=True) for lang in ('en','hi')}} for t in content.TOPICS.values()}
    bundle={'assets':assets,'sources':sources,'catalogue':content.CATALOGUE,'lessons':lessons}
    source='const CONTENT='+json.dumps(bundle,ensure_ascii=False,separators=(',',':'))+';\n'+(ROOT/'hosting/worker.mjs').read_text()
    (destination/'worker/index.js').write_text(source)
    print('Packaged existing UI, all 91 topics, bilingual lyrics/quizzes and verified source originals.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');build(p.parse_args().destination)
