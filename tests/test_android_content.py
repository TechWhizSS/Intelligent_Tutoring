"""Verify the APK bundles the same uploaded academic hierarchy as the website."""
import json
from pathlib import Path
import unittest
from app import content

class AndroidContentTests(unittest.TestCase):
    def test_native_curriculum_matches_every_uploaded_topic(self):
        root=Path(__file__).resolve().parents[1]
        bundle=json.loads((root/'android/app/src/main/assets/syllabus.json').read_text())
        self.assertEqual(bundle['languages'],['en','hi'])
        self.assertEqual(len(bundle['topics']),91)
        for original,android in zip(content.CATALOGUE['topics'],bundle['topics']):
            for key in ['id','subject','unit','chapter','title','sourceText','source','locator','objectives']:
                self.assertEqual(android[key],original[key],(original['id'],key))
            self.assertEqual(android['hash'],content.source_hash(original))
            for language in ['en','hi']:
                self.assertEqual(android['lyrics'][language],content.demo_lyrics(original,language))
                self.assertEqual(android['quiz'][language],content.quiz(original,language,answers=True))
                self.assertEqual(len(android['quiz'][language]),2)
