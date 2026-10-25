"""Official REST contract/security tests. All audio is a test fixture, not a song."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
import wave
from unittest.mock import patch

from app import free_gpu, providers


class FreeGPUTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / 'music-service.json'
        self.patches = [patch.object(free_gpu, 'CONFIG', self.config),
                        patch.dict(os.environ, {'LOCAL_MUSIC_URL': '', 'LOCAL_MUSIC_API_KEY': ''})]
        for p in self.patches:
            p.start()
        self.connection = 'LOCAL_MUSIC_URL=https://my-test-gpu.trycloudflare.com\nLOCAL_MUSIC_API_KEY=test-only-key\n'

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def test_connection_file_is_data_and_restricts_destinations(self):
        config = free_gpu.parse_connection(self.connection)
        self.assertEqual(config['key'], 'test-only-key')
        for text in [self.connection+'EXEC=anything', 'LOCAL_MUSIC_URL=$(do-not-execute)', '', 'a'*8193]:
            with self.assertRaises(free_gpu.GPUError):
                free_gpu.parse_connection(text)
        for url in ['http://[broken', 'http://169.254.169.254', 'http://gpu.trycloudflare.com',
                    'https://gpu.trycloudflare.com.evil.example', 'https://gpu.trycloudflare.com/path',
                    'https://user:pw@gpu.trycloudflare.com', 'https://gpu.trycloudflare.com:444',
                    'https://gpu.trycloudflare.com?key=secret', 'http://127.0.0.1:8000']:
            with self.assertRaises(free_gpu.GPUError):
                free_gpu.validate(url, 'test')
        for key in ['', 'bad\nheader', 'bad\x7f']:
            with self.assertRaises(free_gpu.GPUError):
                free_gpu.validate('https://gpu.trycloudflare.com', key)

    def test_authenticated_save_is_private_and_failed_probe_preserves_old_config(self):
        with patch.object(free_gpu, 'request', return_value=[]):
            result = free_gpu.save(self.connection)
        self.assertTrue(result['authenticated'])
        self.assertFalse(result['liveAudioVerified'])
        self.assertFalse(result['listeningVerified'])
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        before = self.config.read_bytes()
        with patch.object(free_gpu, 'request', side_effect=free_gpu.GPUError('offline')):
            with self.assertRaises(free_gpu.GPUError):
                free_gpu.save(self.connection.replace('test-only-key', 'new-key'))
        self.assertEqual(before, self.config.read_bytes())
        free_gpu.disconnect()
        self.assertIsNone(free_gpu.settings())

    def test_probe_rejects_nonstandard_health_response(self):
        with patch.object(free_gpu, 'request', return_value={'ok': True}):
            with self.assertRaises(free_gpu.GPUError):
                free_gpu.probe(free_gpu.parse_connection(self.connection))

    def test_rest_payload_polling_and_audio_use_only_configured_origin(self):
        calls=[]
        native=providers.build_request('[Verse]\nReviewed words\n[Chorus]\nहिंदी','Hindi',{'tempo':110,'length':30})
        def network(config,path,data=None,audio=False):
            calls.append((config,path,data,audio))
            if path=='/release_task':return {'task_id':'job-1'}
            if len(calls)==2:return [{'task_id':'job-1','status':0}]
            if path=='/query_result':return [{'task_id':'job-1','status':1,'result':json.dumps([{'file':'https://evil.example/v1/audio?path=test.wav','lyrics':native['lyrics']}])}]
            self.assertEqual(path,'/v1/audio?path=test.wav')
            return b'test-contract-audio'
        with patch.object(free_gpu,'settings',return_value=free_gpu.parse_connection(self.connection)),patch.object(free_gpu,'request',side_effect=network),patch.object(free_gpu.time,'sleep'):
            data,words=free_gpu.render(native)
        self.assertEqual(data,b'test-contract-audio');self.assertEqual(words,native['lyrics'])
        body=calls[0][2]
        self.assertEqual(body['lyrics'],native['lyrics']);self.assertEqual(body['vocal_language'],'hi')
        self.assertEqual(body['audio_duration'],30);self.assertEqual(body['bpm'],110)
        self.assertEqual(body['audio_format'],'wav');self.assertFalse(body['thinking'])
        self.assertNotIn('synth_model',body);self.assertNotIn('output_format',body)
        self.assertTrue(all(c[0]['url']=='https://my-test-gpu.trycloudflare.com' for c in calls))

    def test_failed_jobs_and_wrong_task_ids_never_produce_audio(self):
        for row in [{'task_id':'job','status':2,'result':'secret traceback'},
                    {'task_id':'someone-else','status':1},
                    {'task_id':'job','status':1,'result':json.dumps([{'file':'/other/audio'}])}]:
            with patch.object(free_gpu,'settings',return_value=free_gpu.parse_connection(self.connection)),patch.object(free_gpu,'request',side_effect=[{'task_id':'job'},[row]]) as network:
                with self.assertRaises(free_gpu.GPUError) as error:
                    free_gpu.render(providers.build_request('Original words','English',{}))
                self.assertNotIn('secret traceback',str(error.exception))
                self.assertEqual(network.call_count,2)

    def test_timeout_does_not_become_audio(self):
        with patch.object(free_gpu,'settings',return_value=free_gpu.parse_connection(self.connection)),patch.object(free_gpu,'request',return_value={'task_id':'job'}),patch.object(free_gpu.time,'monotonic',side_effect=[0,2000]):
            with self.assertRaisesRegex(free_gpu.GPUError,'time limit'):
                free_gpu.render(providers.build_request('words','English',{}))

    def test_auth_header_json_bounds_and_no_secret_in_public_errors(self):
        config=free_gpu.parse_connection(self.connection)
        opener=type('Opener',(),{})()
        opener.open=lambda request,**kwargs: io.BytesIO(b'{"code":200,"data":[]}')
        with patch.object(free_gpu.urllib.request,'build_opener',return_value=opener):
            self.assertEqual(free_gpu.request(config,'/query_result',{'task_id_list':[]}),[])
        def denied(request,**kwargs):
            self.assertEqual(request.get_header('Authorization'),'Bearer test-only-key')
            self.assertEqual(json.loads(request.data),{'task_id_list':[]})
            raise urllib.error.HTTPError(request.full_url,403,'secret-test-only-key',{},None)
        opener.open=denied
        with patch.object(free_gpu.urllib.request,'build_opener',return_value=opener):
            with self.assertRaises(free_gpu.GPUError) as error:
                free_gpu.request(config,'/query_result',{'task_id_list':[]})
        self.assertNotIn('test-only-key',str(error.exception))
        self.assertIsNone(free_gpu.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.example'))
        opener.open=lambda *a,**k: io.BytesIO(b'x'*1_000_001)
        with patch.object(free_gpu.urllib.request,'build_opener',return_value=opener):
            with self.assertRaisesRegex(free_gpu.GPUError,'oversized'):
                free_gpu.request(config,'/query_result',{})

    def test_provider_routes_real_returned_bytes_and_validates_wav(self):
        self.config.write_text(json.dumps(free_gpu.parse_connection(self.connection)))
        self.assertTrue(providers.configured())
        self.assertEqual(providers.provider_name(),free_gpu.PROVIDER)
        self.assertEqual(providers.music_model(),'acestep-v15-turbo')
        fixture=io.BytesIO()
        with wave.open(fixture,'wb') as w:
            w.setparams((1,2,8000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*8000)
        with patch.object(free_gpu,'render',return_value=(fixture.getvalue(),'returned lyrics')):
            self.assertEqual(providers.music('saved words','English',{}),(fixture.getvalue(),'audio/wav','returned lyrics'))
        with patch.object(free_gpu,'render',return_value=(b'<html>not audio</html>','')):
            with self.assertRaises(providers.ProviderError):providers.music('saved words','English',{})
        self.assertFalse(providers.LOCK.locked())

    def test_notebook_cells_are_valid_python_and_have_no_saved_output(self):
        root=Path(__file__).resolve().parents[1]
        nb=json.loads((root/'notebooks/Free_Singing_GPU.ipynb').read_text())
        for i,cell in enumerate(nb['cells']):
            if cell['cell_type']=='code':
                compile(''.join(cell['source']),f'cell-{i}','exec')
                self.assertEqual(cell['outputs'],[])
                self.assertIsNone(cell['execution_count'])


if __name__=='__main__':unittest.main()
