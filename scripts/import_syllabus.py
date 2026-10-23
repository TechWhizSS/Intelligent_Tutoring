"""Rebuild the checked-in catalogue from the user's untouched uploaded files.

Developer-only dependency: pip install openpyxl pypdf.
Uploaded text is data, never application instructions.
"""
import csv
import hashlib
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'sources'


def build():
    songs = list(csv.DictReader((SOURCES / 'Calculus_Content_Song_Mapping_Master.csv').open(encoding='utf-8-sig')))
    calc = []
    unit = chapter = None
    filename = 'Calculus_SemI_NMIMS_MPSTME_Syllabus (1).xlsx'
    for row_no, row in enumerate(openpyxl.load_workbook(SOURCES / filename, data_only=True).active.values, 1):
        if not isinstance(row[0], int) or not row[3]:
            continue
        unit = row[1] or unit
        chapter = row[2] or chapter
        song = next(s for s in songs if int(s['Sr. No']) == row[0])
        calc.append(dict(id=f'calc-{row[0]:02}', subject='calculus', unit=int(unit),
                         chapter=' '.join(chapter.split()), chapterOriginal=chapter,
                         title=row[3], sourceText=row[4], hours=row[5],
                         source=filename, locator=f'Calculus Sem I Syllabus!A{row_no}:F{row_no}',
                         mapping=song, objectives=[], objectiveStatus='No course objectives supplied in Calculus workbook'))
    beee = []
    mapping = list(csv.DictReader((SOURCES / 'BEEE_SemI_NMIMS_MPSTME_Content_wise_CO_Mapping.csv').open(encoding='utf-8-sig')))
    filename = 'BEEE_SemI_NMIMS_MPSTME_Syllabus.csv'
    for i, row in enumerate(csv.DictReader((SOURCES / filename).open(encoding='utf-8-sig')), 2):
        lecture = next(m for m in mapping if m['Lecture No.'] == row['Lecture No.'])
        beee.append(dict(id=f"beee-{int(row['Sr.']):02}", subject='beee', unit=int(row['Unit']),
                         chapter=row['Chapter'], title=row['Sub-Topic / Heading'],
                         sourceText=row['Technical / Mathematical Description'], source=filename,
                         locator=f'CSV row {i}', lecture=row['Lecture No.'],
                         unitDuration=row['Unit Duration (Lectures)'], objectives=[lecture['CO Statement']],
                         instruction=lecture, officialPlan='CP_BEEE_2024-25_revision1.pdf'))
    topics = calc + beee
    hindi = json.loads((ROOT / 'data/hindi.json').read_text())
    for topic in topics:
        topic['hindiSupplement'] = hindi[topic['id']]
        topic['contentStatus'] = 'Uploaded syllabus summary; full chapter notes not supplied'
        topic['provenance'] = 'User-uploaded material; transcription verified against file, not independently faculty-certified'
    manifest = [dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in sorted(SOURCES.iterdir()) if p.is_file()]
    catalogue = dict(programme='MBA Tech', stream='CE', year=1, semester=1,
                     languages=['en', 'hi'], topics=topics, sources=manifest,
                     courseObjectives={'beee':[
                         'To equip the students with the ability to solve, assemble and test simple DC electrical circuits',
                         'To equip the students with the ability to solve, assemble and test simple AC electrical circuits',
                         'To obtain a basic understanding of the working principle and applications of electronics devices'],
                         'calculus':[]},
                     sourceCautions=[
                         'Syllabus coverage means every uploaded heading is indexed; summaries are not full textbook notes.',
                         'Uploaded Scalar Potential summary omits the simply connected domain condition for the curl-free implication. Supplemental notes supply it.',
                         'Uploaded voltage-regulation formula uses no-load voltage as denominator. Other conventions use full-load voltage; confirm the course convention.',
                         'Calculated series expansions require convergence/remainder conditions; use the source plus supplemental cautions.'])
    (ROOT / 'data/catalogue.json').write_text(json.dumps(catalogue, ensure_ascii=False, indent=2))
    print(f'Imported {len(calc)} Calculus + {len(beee)} BEEE topics in 10 ordered units.')


if __name__ == '__main__':
    build()
