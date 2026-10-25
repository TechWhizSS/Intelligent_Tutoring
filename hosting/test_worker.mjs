import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const source=await readFile(process.argv[2],'utf8');
const {default:worker}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
class Bucket{
 data=new Map();
 async get(key){const value=this.data.get(key);if(value===undefined)return null;const bytes=typeof value==='string'?new TextEncoder().encode(value):new Uint8Array(value);return {json:async()=>JSON.parse(new TextDecoder().decode(bytes)),arrayBuffer:async()=>bytes.buffer,body:new ReadableStream({start(c){c.enqueue(bytes);c.close()}})}}
 async put(key,value){this.data.set(key,typeof value==='string'?value:value.slice());return {}}
 async delete(key){this.data.delete(key)}
 async list({prefix}){return {objects:[...this.data.keys()].filter(k=>k.startsWith(prefix)).map(key=>({key})),truncated:false}}
}
const env={BUCKET:new Bucket()};let cookie='';
async function call(path,body,extra={}){const r=await worker.fetch(new Request('https://test.example'+path,{method:body?'POST':'GET',headers:{'oai-authenticated-user-id':'test-owner','Cookie':cookie,...(body?{'Content-Type':'application/json'}:{}),...extra},body:body?JSON.stringify(body):undefined}),env,{});if(r.headers.get('Set-Cookie'))cookie=r.headers.get('Set-Cookie').split(';')[0];return {status:r.status,headers:r.headers,body:r.headers.get('Content-Type')?.includes('application/json')?await r.json():await r.arrayBuffer()}}
assert.equal((await call('/')).status,200);
assert.equal((await call('/api/catalogue')).status,401);
assert.equal((await call('/api/login',{sap:'70572400001',password:'sample'})).status,200);
assert.equal((await call('/api/catalogue')).body.topics.length,91);
assert.equal((await call('/api/songs')).body.length,4);
for(const topic of ['calc-01','beee-01'])for(const language of ['en','hi']){
 const draft=await call('/api/lyrics',{topic,language});assert.equal(draft.status,201);assert.match(draft.body.lyrics,/\[Chorus\]/);
 const song=draft.body;
 assert.equal((await call(`/api/songs/${song.id}/save`,{lyrics:song.lyrics+'\nReviewed'})).status,200);
 const synth=await call(`/api/songs/${song.id}/synthesize`,{});assert.equal(synth.status,503);assert.match(synth.body.error,/No song was fabricated/);
 assert.equal((await call(`/api/topics/${topic}/quiz?language=${language}`)).body.questions.length,2);
 assert.equal((await call('/api/quiz/submit',{topic,language,answers:[0,0]})).status,200);
}
assert.equal((await call('/api/coverage')).body.topics.length,91);
assert.equal((await call('/api/coverage.csv')).status,200);
assert.equal((await call('/api/sources/Calculus_Content_Song_Mapping_Master.csv')).status,200);
assert.equal((await call('/api/admin/music-service',{local:true})).status,403);
assert.equal((await call('/api/lyrics',{topic:'calc-01',language:'fr'})).status,400);
assert.equal((await call('/api/lyrics',{topic:'calc-01'},{Origin:'https://evil.example'})).status,403);
// Test-only WAV checks audio persistence, byte ranges and list filtering; it is not a song.
const draft=(await call('/api/lyrics',{topic:'beee-01'})).body;const bytes=new Uint8Array(16044);const v=new DataView(bytes.buffer);const ascii=(offset,text)=>[...text].forEach((c,i)=>bytes[offset+i]=c.charCodeAt(0));ascii(0,'RIFF');v.setUint32(4,16036,true);ascii(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,8000,true);v.setUint32(28,16000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);ascii(36,'data');v.setUint32(40,16000,true);
const uploaded=await call(`/api/songs/${draft.id}/upload-audio`,{mime:'audio/wav',data:Buffer.from(bytes).toString('base64'),permitted:true});assert.equal(uploaded.status,200);assert.match(uploaded.body.audio_origin,/User supplied/);
assert.equal((await call('/api/songs')).status,200);
const range=await call(uploaded.body.audioUrl,undefined,{Range:'bytes=0-43'});assert.equal(range.status,206);assert.equal(range.body.byteLength,44);
await call('/api/login',{sap:'admin',password:'demo-admin'});
assert.equal((await call('/api/admin/music-service',{configuration:'NOT_A_CONNECTION=test'})).status,400);
const u=await call('/api/admin/uploads',{topic:'beee-01',name:'notes.txt',excerpt:'An academic reference about resistance.'});assert.equal(u.status,201);
assert.equal((await call(`/api/admin/uploads/${u.body.id}/approve`,{})).status,200);
assert.equal((await call('/api/topics/beee-01')).body.uploads.length,1);
assert.equal((await call('/api/providers')).body.liveAudioVerified,false);
const nativeFetch=globalThis.fetch;let remoteCalls=[];
globalThis.fetch=async(url,options)=>{remoteCalls.push([url,options]);const body=options.body?JSON.parse(options.body):null;if(url.endsWith('/release_task'))return new Response(JSON.stringify({code:200,data:{task_id:'test-task'}}));if(body?.task_id_list?.[0])return new Response(JSON.stringify({code:200,data:[{task_id:'test-task',status:1,result:JSON.stringify([{file:'https://evil.example/v1/audio?path=fixture.wav',lyrics:'test only'}])}]}));if(url.includes('/v1/audio?'))return new Response(bytes,{headers:{'Content-Type':'audio/wav'}});return new Response(JSON.stringify({code:200,data:[]}))};
try{
 const config='LOCAL_MUSIC_URL=https://test-gpu.trycloudflare.com\nLOCAL_MUSIC_API_KEY=test-only-private-key';
 assert.equal((await call('/api/admin/music-service',{configuration:config})).status,200);
 const p=(await call('/api/providers')).body;assert.equal(p.configured,true);assert.ok(!JSON.stringify(p).includes('test-only-private-key'));
 const d=(await call('/api/lyrics',{topic:'calc-01',language:'hi'})).body;
 assert.equal((await call(`/api/songs/${d.id}/synthesize`,{})).body.status,'generating');
 const ready=(await call('/api/songs')).body.find(s=>s.id===d.id);assert.equal(ready.status,'ready');assert.equal(ready.audio_origin,'ACE-Step 1.5 connected GPU');
 assert.ok(remoteCalls.every(([url])=>url.startsWith('https://test-gpu.trycloudflare.com/')));
 const generated=await call(ready.audioUrl);assert.equal(generated.status,200);assert.equal(generated.body.byteLength,bytes.length);
 assert.ok(!JSON.stringify(ready).includes('gpuVersion'));
}finally{globalThis.fetch=nativeFetch}

// Official ElevenLabs protocol. These are controlled fixtures, not live songs.
assert.equal((await call('/api/admin/elevenlabs',{apiKey:'bad\nheader-key'})).status,400);
let elevenTier='free',musicCalls=0,blockMusic=true;
globalThis.fetch=async(url,options={})=>{
 assert.ok(url.startsWith('https://api.elevenlabs.io/v1/'));assert.equal(options.headers['xi-api-key'],'test-only-eleven-key');
 if(url.endsWith('/user/subscription'))return new Response(JSON.stringify({tier:elevenTier,character_count:0,character_limit:10000}));
 if(url.includes('/music?')){musicCalls++;if(blockMusic)return new Response('{}',{status:403});const body=JSON.parse(options.body);assert.equal(body.model_id,'music_v2_5');assert.ok(body.composition_plan.chunks[0].text.includes('[Verse]'));assert.equal(body.composition_plan.chunks.reduce((n,c)=>n+c.duration_ms,0),30000);assert.ok(!body.prompt);const mp3=new Uint8Array(2000);mp3.set([73,68,51]);return new Response(mp3)}
 throw new Error('Unexpected request');
};
try{
 const checked=await call('/api/admin/elevenlabs',{apiKey:'test-only-eleven-key'});assert.equal(checked.status,200);assert.equal(checked.body.musicAccessVerified,false);
 assert.ok(!JSON.stringify((await call('/api/providers')).body).includes('test-only-eleven-key'));
 const song=(await call('/api/lyrics',{topic:'calc-01',language:'hi'})).body;
 const blocked=await call(`/api/songs/${song.id}/synthesize`,{provider:'elevenlabs'});assert.equal(blocked.status,503);assert.match(blocked.body.error,/paid subscription/);assert.equal((await call('/api/songs')).body.find(s=>s.id===song.id).status,'failed');
 elevenTier='starter';const before=musicCalls;assert.equal((await call(`/api/songs/${song.id}/synthesize`,{provider:'elevenlabs'})).status,503);assert.equal(musicCalls,before); // no paid-tier call under free-only authorization
 elevenTier='free';blockMusic=false;
 const ready=await call(`/api/songs/${song.id}/synthesize`,{provider:'elevenlabs'});assert.equal(ready.status,200);assert.equal(ready.body.status,'ready');assert.equal(ready.body.audio_origin,'ElevenLabs Music v2.5');assert.equal((await call(ready.body.audioUrl)).body.byteLength,2000);
}finally{globalThis.fetch=nativeFetch}
console.log('PASS hosted API: 91 topics, bilingual drafts/quizzes, persistent sessions/library/uploads, audio ranges, GPU protocol/authentication, owner isolation and honest blockers. Audio is an isolated fixture.');
