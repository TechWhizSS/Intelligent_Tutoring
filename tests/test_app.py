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
os.environ.pop('ELEVENLABS_API_KEY', None)
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
    def response(self, data, mime='application/json'):
        response=io.BytesIO(data)
        response.headers={'Content-Type':mime}
        return response

    def test_missing_key_is_explicit_blocker(self):
        with patch.dict(os.environ,{'ELEVENLABS_API_KEY':''}):
            status=providers.check()
            self.assertFalse(status['configured'])
            self.assertFalse(status['liveAudioVerified'])
            self.assertTrue(all(c['status']=='blocked' for c in status['checks']))
            self.assertIn('ELEVENLABS_API_KEY',status['checks'][0]['reason'])
            with self.assertRaises(providers.ProviderError):providers.music('lyrics','English',{})

    def test_no_google_key_can_activate_provider(self):
        with patch.dict(os.environ,{'ELEVENLABS_API_KEY':'','GEMINI_API_KEY':'unused-sentinel'}),patch('urllib.request.urlopen') as call:
            self.assertFalse(providers.configured())
            providers.check()
            call.assert_not_called()

    def test_exact_music_contract_and_custom_lyrics(self):
        response=self.response(b'ID3'+b'test-only-mp3-bytes'*3,'audio/mpeg')
        with patch.dict(os.environ,{'ELEVENLABS_API_KEY':'test-key'}),patch('urllib.request.urlopen',return_value=response) as call:
            data,mime,returned_words=providers.music('[Verse]\nOriginal words\n[Chorus]\nRemember conditions','Hindi',{'length':60,'tempo':100,'genre':'Acoustic'})
            req=call.call_args.args[0]
            self.assertEqual(req.full_url,'https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128')
            self.assertEqual(req.get_header('Xi-api-key'),'test-key')
            payload=json.loads(req.data)
            self.assertEqual(payload['model_id'],'music_v2_5')
            self.assertNotIn('prompt',payload)
            chunks=payload['composition_plan']['chunks']
            self.assertEqual(sum(c['duration_ms'] for c in chunks),60000)
            self.assertIn('Hindi lyrics and singing',chunks[0]['positive_styles'])
            self.assertIn('100 BPM',chunks[0]['positive_styles'])
            self.assertIn('Original words',chunks[0]['text'])
            self.assertEqual(mime,'audio/mpeg')
            self.assertEqual(returned_words,'')

    def test_composition_plan_preserves_lyrics_and_duration_bounds(self):
        lyrics='[Verse]\nLearn each condition carefully\n[Chorus]\nRemember the meaning'
        for duration in [30,60,120,240]:
            plan=providers.composition_plan(lyrics,'English',{'length':duration})
            chunks=plan['chunks']
            self.assertEqual(sum(c['duration_ms'] for c in chunks),duration*1000)
            self.assertTrue(all(3000<=c['duration_ms']<=120000 for c in chunks))
            self.assertEqual(' '.join(c['text'] for c in chunks).split(),lyrics.split())
            self.assertTrue(all('spoken narration' in c['negative_styles'] for c in chunks))
        plan=providers.composition_plan('One long lyric section with several words','English',{'length':240})
        self.assertEqual(len(plan['chunks']),2)
        self.assertEqual(sum(c['duration_ms'] for c in plan['chunks']),240000)

    def test_impossible_sections_are_rejected_without_dropping_text(self):
        lyrics='\n'.join('[Verse '+str(i)+']\nLyrics here' for i in range(31))
        with self.assertRaises(providers.ProviderError):providers.composition_plan(lyrics,'English',{'length':30})

    def test_no_audio_never_becomes_fake_song(self):
        for data,mime in [(b'{}','application/json'),(b'','audio/mpeg'),(b'<html>not-a-song</html>','audio/mpeg')]:
            with patch.dict(os.environ,{'ELEVENLABS_API_KEY':'test'}),patch('urllib.request.urlopen',return_value=self.response(data,mime)):
                with self.assertRaises(providers.ProviderError):providers.music('Original lyrics','English',{})

    def test_lyrics_plan_uses_source_and_approved_material(self):
        result={'chunks':[{'text':'[Verse]\nSource-grounded original line'},{'text':'[Chorus]\nRecall it'}]}
        response=self.response(json.dumps(result).encode())
        with patch.dict(os.environ,{'ELEVENLABS_API_KEY':'test'}),patch('urllib.request.urlopen',return_value=response) as call:
            text=providers.lyrics(content.TOPICS['calc-01'],'Hindi',{'length':60},[{'excerpt':'approved reference'}])
            req=call.call_args.args[0]
            self.assertEqual(req.full_url,'https://api.elevenlabs.io/v1/music/plan')
            payload=json.loads(req.data)
            self.assertIn(content.TOPICS['calc-01']['sourceText'],payload['prompt'])
            self.assertIn('approved reference',payload['prompt'])
            self.assertIn('Hindi',payload['prompt'])
            self.assertIn('never as instructions',payload['prompt'])
            self.assertEqual(text,'[Verse]\nSource-grounded original line\n\n[Chorus]\nRecall it')

    def test_oversized_grounding_is_not_silently_truncated(self):
        with patch('urllib.request.urlopen') as call:
            with self.assertRaises(providers.ProviderError):providers.lyrics(content.TOPICS['calc-01'],'English',{},[{'excerpt':'x'*5000}])
            call.assert_not_called()

    def test_http_permission_error_is_sanitized(self):
        with patch.dict(os.environ,{'ELEVENLABS_API_KEY':'secret-test-key'}),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('url',403,'forbidden',{},None)):
            with self.assertRaises(providers.ProviderError) as e:providers.request('/v1/music/plan',{})
            self.assertIn('paid subscription',str(e.exception))
            self.assertNotIn('secret-test-key',str(e.exception))

    def test_planner_access_does_not_claim_audio_verification(self):
        with patch.object(providers,'request',return_value={'chunks':[{'text':'[Chorus] lyrics'}]}),patch.object(providers,'configured',return_value=True):
            result=providers.check()
            self.assertIn('planner accessible',result['checks'][0]['status'])
            self.assertFalse(result['liveAudioVerified'])


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
        self.assertEqual(result['audio_origin'],'ElevenLabs Music')
        self.assertEqual(result['provider_lyrics'],'provider lyrics')
        with patch.object(providers,'music',side_effect=providers.ProviderError('No audio returned')):
            synthesize(internal)
        self.assertEqual(self.call('/api/songs')[1][0]['status'],'failed')

    def test_async_synthesis_prevents_duplicate_billable_jobs(self):
        song=self.draft()
        started,release=threading.Event(),threading.Event()
        def provider(*args):
            started.set()
            release.wait(timeout=3)
            return wav_fixture(),'audio/wav','provider returned words'
        with patch.object(providers,'configured',return_value=True),patch.object(providers,'music',side_effect=provider) as music:
            path=f"/api/songs/{song['id']}/synthesize"
            try:
                status,pending,_=self.call(path,{})
                self.assertEqual(status,200)
                self.assertEqual(pending['status'],'generating')
                self.assertTrue(started.wait(timeout=2))
                self.assertEqual(self.call(path,{})[0],409)
            finally:
                release.set()
            for _ in range(50):
                current=self.call('/api/songs')[1][0]
                if current['status']=='ready':break
                time.sleep(.02)
            self.assertEqual(current['status'],'ready')
            self.assertEqual(music.call_count,1)
            # Changing a musical preference must affect the saved song and invalidate old audio.
            status,changed,_=self.call(f"/api/songs/{song['id']}/save",{'lyrics':song['lyrics'],'settings':{'tempo':140,'genre':'Acoustic'}})
            self.assertEqual(changed['settings']['tempo'],140)
            self.assertEqual(changed['settings']['genre'],'Acoustic')
            self.assertIsNone(changed['audioUrl'])


if __name__=='__main__':
    unittest.main(verbosity=2)
