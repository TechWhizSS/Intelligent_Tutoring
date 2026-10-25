"""Bundle the same verified syllabus and labelled supplements into the Android app."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import content

def build():
    rows=[]
    for i,t in enumerate(content.CATALOGUE['topics']):
        rows.append({**t,'index':i,'hash':content.source_hash(t),'supplemental':content.supplemental(t),
            'lyrics':{lang:content.demo_lyrics(t,lang) for lang in ('en','hi')},
            'quiz':{lang:content.quiz(t,lang,answers=True) for lang in ('en','hi')}})
    path=ROOT/'android/app/src/main/assets/syllabus.json'
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps({'languages':['en','hi'],'topics':rows},ensure_ascii=False,indent=2)+'\n')
    print(f'Bundled {len(rows)} uploaded syllabus topics with bilingual drafts, quizzes and source provenance.')
if __name__=='__main__':build()
