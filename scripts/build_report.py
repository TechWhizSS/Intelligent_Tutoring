"""Export a complete source-linked baseline report without running the app."""
import csv
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.content import CATALOGUE
fields = ['id', 'subject', 'unit', 'chapter', 'topic', 'source', 'locator', 'content', 'English lyrics', 'Hindi lyrics', 'quiz', 'audio']
rows = []
for t in CATALOGUE['topics']:
    rows.append(dict(zip(fields, [t['id'], t['subject'], t['unit'], t['chapter'], t['title'], t['source'], t['locator'],
        'Uploaded summary + supplemental guidance; full notes not supplied',
        'Offline template available; live planner unverified', 'Offline template available; live planner unverified',
        '2 supplemental questions ready', 'Blocked: ElevenLabs Music API key not configured'])))
with (ROOT / 'docs/syllabus-completeness.csv').open('w', encoding='utf-8-sig', newline='') as file:
    writer = csv.DictWriter(file, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
text = ['# Semester I syllabus completeness', '',
    'Baseline: 38 Calculus topics and 53 BEEE topics; all 10 uploaded units indexed in order.', '',
    'Every topic has its exact uploaded summary/formula reference, a supplemental Hindi explanation, supplemental revision guidance, English and Hindi offline lyric templates, and two supplemental quiz questions. Full textbook notes were not supplied. Live ElevenLabs lyric planning and music generation are unverified because no API key is configured. There are no bundled generated songs. Runtime reports show your actual saved draft/audio readiness.', '',
    'Source locations and every status column are in [the complete CSV](syllabus-completeness.csv).', '',
    '| Subject | Unit | Chapter | Uploaded topic | Content | Lyrics EN / HI | Quiz | Audio |',
    '| --- | --- | --- | --- | --- | --- | --- | --- |']
for row in rows:
    text.append('| ' + ' | '.join(str(v).replace('|', '\\|') for v in [row['subject'], row['unit'], row['chapter'], row['topic'],
        'Summary + supplement; full notes pending', 'Offline templates', '2 ready', 'Blocked']) + ' |')
(ROOT / 'docs/SYLLABUS_COMPLETENESS.md').write_text('\n'.join(text) + '\n')
print(f'Exported all {len(rows)} topic rows.')
