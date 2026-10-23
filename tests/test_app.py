"""Meaningful catalogue, API, authorization, persistence and provider contract tests.
Audio bytes used here are test-only WAV fixtures, never educational demo songs.
"""
import base64
import contextlib
import http.cookiejar
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave
from pathlib import Path
from unittest.mock import patch

TEMP = tempfile.TemporaryDirectory()
os.environ['APP_DATA_DIR'] = TEMP.name
os.environ.pop('GEMINI_API_KEY', None)
from app import content, providers, store
from app.server import Handler, ThreadingHTTPServer, synthesize


def wav_fixture():
    output = io.BytesIO()
    with wave.open(output, 'wb') as f:
        f.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        f.writeframes(b'\0\0' * 800)
    return output.getvalue()


class CatalogueTests(unittest.TestCase):
    def test_full_source_coverage_and_unit_order(self):
        self.assertEqual(len(content.TOPICS), 91)
        self.assertEqual([t['unit'] for t in content.TOPICS.values() if t['subject']=='calculus'], [1]*9+[2]*5+[3]*5+[4]*8+[5]*11)
        self.assertEqual([t['unit'] for t in content.TOPICS.values() if t['subject']=='beee'], [1]*11+[2]*13+[3]*8+[4]*10+[5]*11)
        self.assertEqual(content.CATALOGUE['languages'], ['en','hi'])

    def test_all_sources_exist_and_hashes_match(self):
        import hashlib
        for source in content.CATALOGUE['sources']:
            self.assertEqual(hashlib.sha256((content.ROOT/'sources'/source['file']).read_bytes()).hexdigest(),source['sha256'])

    def test_every_topic_has_bilingual_template_and_quiz(self):
        for topic in content.TOPICS.values():
            self.assertTrue(topic['sourceText'])
            self.assertTrue(topic['locator'])
            self.assertTrue(topic['hindiSupplement'])
            for language in ['en','hi']:
                self.assertIn('[Chorus]', content.demo_lyrics(topic,language))
                questions=content.quiz(topic,language,answers=True)
                public=content.quiz(topic,language)
                self.assertEqual(len(questions),2)
                for private,q in zip(questions,public):
                    self.assertEqual(len(set(q['options'])),4)
                    self.assertNotIn('correct',q)
                    self.assertEqual(q['options'][private['correct']],topic['hindiSupplement'] if private['id']=='meaning' and language=='hi' else topic['sourceText'] if private['id']=='meaning' else topic['title'])

    def test_uploaded_formula_and_scope_preserved(self):
        self.assertIn("f'(c) = 0",content.TOPICS['calc-01']['sourceText'])
        self.assertIn('excluding supermesh',content.TOPICS['beee-06']['title'])
        self.assertIn('CO1',content.TOPICS['beee-01']['objectives'][0])
        self.assertIn('simply connected',' '.join(content.supplemental(content.TOPICS['calc-32'])))


class ProviderTests(unittest.TestCase):
    def test_missing_key_is_explicit_blocker(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':''}):
            status=providers.check()
            self.assertFalse(status['configured'])
            self.assertFalse(status['liveAudioVerified'])
            self.assertTrue(all(c['status']=='blocked' for c in status['checks']))
            with self.assertRaises(providers.ProviderError):providers.music('lyrics','English',{})

    def test_audio_can_follow_text_or_thought_parts(self):
        result={'candidates':[{'content':{'parts':[{'text':'thinking','thought':True},{'text':'returned lyrics'},{'inlineData':{'mimeType':'audio/mpeg','data':base64.b64encode(b'ID3actualtestaudio').decode()}}]}}]}
        with patch.object(providers,'generate',return_value=result) as generate:
            data,mime,lyrics=providers.music('[Chorus] test','Hindi',{'tempo':100})
            self.assertEqual(data,b'ID3actualtestaudio')
            self.assertEqual(mime,'audio/mpeg')
            self.assertEqual(lyrics,'returned lyrics')
            prompt=generate.call_args.args[1]
            self.assertIn('sung vocals',prompt)
            self.assertIn('Hindi',prompt)
            self.assertEqual(generate.call_args.args[0],'lyria-3.5')

    def test_no_audio_never_becomes_fake_song(self):
        with patch.object(providers,'generate',return_value={'candidates':[{'content':{'parts':[{'text':'blocked'}]}}]}):
            with self.assertRaises(providers.ProviderError):providers.music('lyrics','English',{})

    def test_lyrics_use_source_and_approved_material_only(self):
        with patch.object(providers,'generate',return_value={'candidates':[{'content':{'parts':[{'text':'[Chorus] Original lyrics'}]}}]}) as generate:
            result=providers.lyrics(content.TOPICS['calc-01'],'Hindi',{'genre':'Pop'},[{'excerpt':'approved reference'}])
            self.assertIn('[Chorus]',result)
            prompt=json.loads(generate.call_args.args[1])
            self.assertEqual(prompt['ACADEMIC_SOURCE'],content.TOPICS['calc-01']['sourceText'])
            self.assertEqual(prompt['language'],'Hindi')
            self.assertIn('untrusted',generate.call_args.args[2])

    def test_http_permission_error_is_sanitized(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'secret-test-key'}),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('url',403,'forbidden',{},None)):
            with self.assertRaises(providers.ProviderError) as e:providers.request('/models/lyria-3.5')
            self.assertIn('billing',str(e.exception))
            self.assertNotIn('secret-test-key',str(e.exception))

    def test_exact_documented_rest_contract(self):
        response=io.BytesIO(json.dumps({'candidates':[]}).encode())
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}),patch('urllib.request.urlopen',return_value=response) as call:
            providers.generate('lyria-3.5','original sung lyrics')
            req=call.call_args.args[0]
            self.assertEqual(req.full_url,'https://generativelanguage.googleapis.com/v1beta/models/lyria-3.5:generateContent')
            self.assertEqual(json.loads(req.data),{'contents':[{'role':'user','parts':[{'text':'original sung lyrics'}]}]})


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store.init()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def setUp(self):
        self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.sap='test-'+os.urandom(4).hex()
        self.call('/api/login',{'sap':self.sap,'password':'anything'})

    def call(self,path,body=None,client=None,headers=None,raw=False):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with (client or self.client).open(req) as r:
                data=r.read()
                return r.status,data if raw else json.loads(data),r.headers
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read()),e.headers

    def draft(self,topic='calc-01',language='en'):
        status,song,_=self.call('/api/lyrics',{'topic':topic,'language':language,'mode':'demo'})
        self.assertEqual(status,201,song)
        self.assertIsNone(song['audioUrl'])
        self.assertIn('Offline template',song['provenance'])
        return song

    def test_login_cookie_and_session(self):
        status,me,_=self.call('/api/me')
        self.assertEqual(status,200)
        self.assertEqual(me['sap'],self.sap)
        status,result,headers=self.call('/api/login',{'sap':self.sap,'password':'arbitrary'})
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertTrue(result['sampleLogin'])
        self.call('/api/logout',{})
        self.assertEqual(self.call('/api/me')[0],401)

    def test_anonymous_access_is_denied(self):
        client=urllib.request.build_opener()
        for path in ['/api/catalogue','/api/songs','/api/coverage']:
            self.assertEqual(self.call(path,client=client)[0],401)

    def test_both_subject_end_to_end_offline_and_audio_blocker(self):
        for topic in ['calc-01','beee-01']:
            for language in ['en','hi']:
                song=self.draft(topic,language)
                updated=song['lyrics']+'\nReviewed revision'
                status,saved,_=self.call(f"/api/songs/{song['id']}/save",{'lyrics':updated})
                self.assertEqual(status,200)
                self.assertEqual(saved['lyrics'],updated)
                status,error,_=self.call(f"/api/songs/{song['id']}/synthesize",{})
                self.assertEqual(status,503)
                self.assertIn('No song was fabricated',error['error'])
                qs=content.quiz(content.TOPICS[topic],language,answers=True)
                status,result,_=self.call('/api/quiz/submit',{'topic':topic,'language':language,'answers':[q['correct'] for q in qs]})
                self.assertEqual(result['score'],2)
        self.assertEqual(len(self.call('/api/songs')[1]),4)
        self.assertEqual(len(self.call('/api/attempts')[1]),4)

    def test_language_and_setting_validation(self):
        self.assertEqual(self.call('/api/lyrics',{'topic':'calc-01','language':'fr'})[0],400)
        self.assertEqual(self.call('/api/lyrics',{'topic':'calc-01','settings':{'tempo':900}})[0],400)
        self.assertEqual(self.call('/api/lyrics',{'topic':'calc-01','settings':{'genre':'unsupported'}})[0],400)
        self.assertEqual(self.call('/api/lyrics',{'topic':'not-a-topic'})[0],404)
        self.assertEqual(self.call('/api/topics/calc-01/quiz?language=fr')[0],400)

    def test_source_download_and_traversal(self):
        status,data,headers=self.call('/api/sources/Calculus_Content_Song_Mapping_Master.csv',raw=True)
        self.assertEqual(status,200)
        self.assertIn(b"Rolle's Theorem",data)
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(self.call('/api/sources/../../.env')[0],404)

    def test_song_isolation(self):
        song=self.draft()
        other=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.call('/api/login',{'sap':'another-'+os.urandom(3).hex(),'password':'anything'},client=other)
        self.assertEqual(self.call('/api/songs',client=other)[1],[])
        self.assertEqual(self.call(f"/api/songs/{song['id']}/save",{'lyrics':'stolen'},client=other)[0],404)
        self.assertEqual(self.call(f"/api/songs/{song['id']}/audio",client=other)[0],404)

    def test_upload_audio_range_download_and_lyric_invalidation(self):
        song=self.draft()
        audio=wav_fixture()
        status,song,_=self.call(f"/api/songs/{song['id']}/upload-audio",{'data':base64.b64encode(audio).decode(),'mime':'audio/wav','permitted':True})
        self.assertEqual(status,200)
        self.assertIn('User supplied',song['audio_origin'])
        status,data,headers=self.call(song['audioUrl'],headers={'Range':'bytes=0-43'},raw=True)
        self.assertEqual(status,206)
        self.assertEqual(data,audio[:44])
        self.assertEqual(headers['Content-Range'],f'bytes 0-43/{len(audio)}')
        self.assertEqual(self.call(song['audioUrl'],headers={'Range':'bytes=999999-'})[0],416)
        status,data,headers=self.call(song['audioUrl']+'?download=1',raw=True)
        self.assertEqual(data,audio)
        self.assertIn('attachment',headers['Content-Disposition'])
        status,edited,_=self.call(f"/api/songs/{song['id']}/save",{'lyrics':'New words, new audio needed'})
        self.assertIsNone(edited['audioUrl'])
        self.assertIsNone(edited['audio_origin'])

    def test_invalid_audio_and_missing_permission(self):
        song=self.draft()
        path=f"/api/songs/{song['id']}/upload-audio"
        self.assertEqual(self.call(path,{'permitted':False})[0],400)
        self.assertEqual(self.call(path,{'permitted':True,'data':base64.b64encode(b'not audio'*10).decode(),'mime':'audio/wav'})[0],400)

    def test_coverage_contains_every_topic_and_honest_status(self):
        status,report,_=self.call('/api/coverage')
        self.assertEqual(report['indexed'],91)
        self.assertEqual(report['fullNotesReady'],0)
        self.assertEqual({t['id'] for t in report['topics']},set(content.TOPICS))
        self.assertTrue(all(t['audio']=='Not generated' for t in report['topics']))
        self.assertEqual(self.call('/api/coverage.csv',raw=True)[1].decode('utf-8-sig').count('\n'),92)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.call('/api/lyrics',{'topic':'calc-01'},headers={'Origin':'https://evil.example'})[0],403)

    def test_admin_upload_review_does_not_rewrite_syllabus(self):
        self.assertEqual(self.call('/api/admin/uploads')[0],403)
        self.assertEqual(self.call('/api/login',{'sap':'admin','password':'wrong'})[0],401)
        self.assertEqual(self.call('/api/login',{'sap':'admin','password':'demo-admin'})[0],200)
        status,upload,_=self.call('/api/admin/uploads',{'topic':'beee-01','name':'faculty-notes.txt','excerpt':'Approved academic reference about resistance.'})
        self.assertEqual(status,201)
        self.assertFalse(upload['approved'])
        self.assertNotIn(upload['id'],[u['id'] for u in self.call('/api/topics/beee-01')[1]['uploads']])
        self.assertEqual(self.call('/api/admin/uploads/'+upload['id']+'/approve',{})[0],200)
        self.assertIn(upload['id'],[u['id'] for u in self.call('/api/topics/beee-01')[1]['uploads']])
        self.assertEqual(len(content.TOPICS),91)

    def test_worker_persists_only_actual_returned_audio(self):
        song=self.draft('beee-01')
        internal=store.rows('SELECT * FROM songs WHERE id=?',(song['id'],))[0]
        with patch.object(providers,'music',return_value=(wav_fixture(),'audio/wav','provider lyrics')):
            synthesize(internal)
        result=self.call('/api/songs')[1][0]
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['audio_origin'],'Lyria 3.5')
        self.assertEqual(result['provider_lyrics'],'provider lyrics')
        with patch.object(providers,'music',side_effect=providers.ProviderError('No audio returned')):
            synthesize(internal)
        self.assertEqual(self.call('/api/songs')[1][0]['status'],'failed')


if __name__=='__main__':
    unittest.main(verbosity=2)
