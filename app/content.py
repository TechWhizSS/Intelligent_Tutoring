import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = json.loads((ROOT / 'data/catalogue.json').read_text())
TOPICS = {t['id']: t for t in CATALOGUE['topics']}
LANGUAGES = {'en': 'English', 'hi': 'Hindi'}


def supplemental(topic):
    notes = ['Identify the assumptions and units before using the uploaded reference.',
             'Write the governing relation, substitute carefully, then check the result against the definition.',
             'These revision prompts and Hindi explanations are supplemental; the uploaded excerpt is a syllabus summary, not full chapter notes.']
    if topic['id'] == 'calc-01':
        notes.append("Worked example (supplemental): f(x)=x^2-1 on [-1,1] is continuous and differentiable. f(-1)=f(1)=0. Since f'(x)=2x, c=0 lies inside (-1,1) and f'(0)=0. Equal endpoint values do not replace the continuity and differentiability conditions.")
        notes.append('हल किया उदाहरण (पूरक): f(x)=x^2-1 के लिए [-1,1] पर दोनों सिरों का मान शून्य है। फलन सतत और अवकलनीय है। f\'(x)=2x से c=0 मिलता है, जो अंतराल के भीतर है।')
    if topic['id'] == 'beee-01':
        notes.append('Worked example (supplemental): A 10 ohm resistor across a 20 V DC source carries I=V/R=2 A. It dissipates P=I^2*R=40 W. A resistor dissipates energy; ideal inductors and capacitors store energy in magnetic and electric fields respectively.')
        notes.append('हल किया उदाहरण (पूरक): 10 ओम प्रतिरोधक पर 20 वोल्ट लगाने पर I=20/10=2 ऐम्पियर और P=2^2*10=40 वाट मिलता है। धारा और शक्ति की इकाइयाँ भी लिखें।')
    if topic['id'] == 'calc-32':
        notes.append('A continuously differentiable curl-free field has a scalar potential on a simply connected open domain. Curl-free alone is insufficient on arbitrary domains.')
    if topic['id'] in ['calc-06', 'calc-07']:
        notes.append('Taylor polynomials include a remainder; an infinite Taylor series represents the function only where the remainder tends to zero.')
    if topic['id'] == 'beee-28':
        notes.append('The uploaded mapping uses no-load voltage in the regulation denominator. Some conventions use full-load voltage. Confirm your course convention before numerical work.')
    return notes


def demo_lyrics(topic, language):
    """Explicit offline template, never passed off as Gemini or generated audio."""
    if language == 'hi':
        return f"[Verse 1]\n{topic['hindiSupplement']}\n\n[Chorus]\nसमझो, दोहराओ, यादों में बसाओ,\nसूत्र की हर शर्त को साथ निभाओ।\nलय में सीखो, फिर सवाल लगाओ,\nहर कदम पर अपना उत्तर जाँचते जाओ।\n\n[Verse 2]\nपुस्तक का संदर्भ साथ रखो,\nपरिभाषा और शर्तों को साफ लिखो।\n{topic['hindiSupplement']}\n\n[Chorus]\nसमझो, दोहराओ, यादों में बसाओ,\nसूत्र की हर शर्त को साथ निभाओ।"
    return f"[Verse 1]\nToday's idea: {topic['title']}.\nRead the reference, take it slow,\nCheck the conditions before you go.\n\n[Reference refrain — adapt the wording before singing]\n{topic['sourceText']}\n\n[Chorus]\nLearn it, sing it, let the meaning stay,\nCheck every condition along the way.\nA rhythm for recall, a reason for each line,\nWork through the question, one step at a time.\n\n[Verse 2]\nSay what each symbol means today,\nThen let the reference lead the way.\n\n[Chorus]\nLearn it, sing it, let the meaning stay,\nCheck every condition along the way."


def quiz(topic, language='en', answers=False):
    """Definition/meaning questions, distractors from other uploaded syllabus topics."""
    rng = random.Random(topic['id'] + language)
    others = [t for t in TOPICS.values() if t['subject'] == topic['subject'] and t['id'] != topic['id']]
    rng.shuffle(others)
    choices = [topic, *others[:3]]
    rng.shuffle(choices)
    field = 'hindiSupplement' if language == 'hi' else 'sourceText'
    questions = [dict(id='meaning', prompt=(f"‘{topic['title']}’ का सही विचार चुनें।" if language == 'hi' else f"Which statement correctly describes {topic['title']}?"),
                      options=[t[field] for t in choices], correct=choices.index(topic), explanation=topic[field])]
    titles = [topic, *others[3:6]]
    rng.shuffle(titles)
    questions.append(dict(id='identify', prompt=(f"यह कथन किस विषय को बताता है? {topic[field]}" if language == 'hi' else f"Which topic is described by this reference? {topic[field]}"),
                          options=[t['title'] for t in titles], correct=titles.index(topic), explanation=topic[field]))
    if answers:
        return questions
    return [{k: v for k, v in q.items() if k not in ('correct', 'explanation')} for q in questions]


def source_hash(topic):
    return hashlib.sha256(topic['sourceText'].encode()).hexdigest()
