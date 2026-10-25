/* Hosted version of the Python API: persistent R2 records + free ACE-Step GPU.
   No CPU model, TTS, oscillator fallback or fabricated educational audio. */
const HEADERS={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; frame-src https://gemini.google.com; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"};
class APIError extends Error {constructor(status,message){super(message);this.status=status}}
const error=(status,message)=>{throw new APIError(status,message)};
const response=(value,status=200,headers={})=>new Response(JSON.stringify(value),{status,headers:{...HEADERS,'Content-Type':'application/json; charset=utf-8',...headers}});
const now=()=>Date.now()/1000;
const uuid=()=>crypto.randomUUID();
const sha=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');
const b64bytes=text=>Uint8Array.from(atob(text),c=>c.charCodeAt(0));
const readJSON=async(bucket,key)=>{const o=await bucket.get(key);return o?o.json():null};
const saveJSON=(bucket,key,value)=>bucket.put(key,JSON.stringify(value),{httpMetadata:{contentType:'application/json'}});
const topic=id=>CONTENT.catalogue.topics.find(t=>t.id===id)||error(404,'Topic not found in the uploaded syllabus.');
function language(value='en'){if(!['en','hi'].includes(value))error(400,'Only English and Hindi are supported.');return value}
function settings(body){
 const supplied=body.settings??{};if(!supplied||typeof supplied!=='object'||Array.isArray(supplied))error(400,'Settings must be an object.');
 const result={};
 for(const [key,choices] of Object.entries({genre:['Pop','Lo-fi','Hip-hop','Acoustic','Electronic','Indian fusion','Rock'],mood:['Uplifting','Calm','Energetic','Focused'],vocal:['Warm','Bright','Low register','High register','Duet','Female vocal','Male vocal'],difficulty:['Beginner','Intermediate','Exam revision']})){
  result[key]=supplied[key]??choices[0];if(!choices.includes(result[key]))error(400,'Unsupported '+key+'.');
 }
 for(const [key,def,min,max] of [['tempo',100,60,180],['length',30,30,240],['formulaRepeats',2,1,4]]){
  result[key]=Number(supplied[key]??def);if(!Number.isInteger(result[key])||result[key]<min||result[key]>max)error(400,`${key} must be between ${min} and ${max}.`);
 }
 result.instructions=String(supplied.instructions??'').slice(0,1500);return result;
}
function publicSong(s){const value={...s,audioUrl:s.audio?`/api/songs/${s.id}/audio`:null};for(const k of ['sap','audio','task','taskStarted','gpuVersion','download'])delete value[k];return value}
function validateConnection(text){
 if(typeof text!=='string'||text.length>8192)error(400,'Choose the small song-service.env file downloaded by the notebook.');
 const values={};for(const line of text.split(/\r?\n/).map(s=>s.trim()).filter(s=>s&&!s.startsWith('#'))){const i=line.indexOf('=');const key=line.slice(0,i).trim();if(i<1||!['LOCAL_MUSIC_URL','LOCAL_MUSIC_API_KEY'].includes(key))error(400,'This is not a supported notebook connection file.');values[key]=line.slice(i+1).trim().replace(/^["']|["']$/g,'')}
 let u;try{u=new URL(values.LOCAL_MUSIC_URL)}catch{error(400,'Invalid GPU service URL.')}
 if(u.protocol!=='https:'||!/^([a-z0-9]+-)*[a-z0-9]+\.trycloudflare\.com$/.test(u.hostname)||u.port||u.username||u.password||u.search||u.hash||u.pathname!=='/')error(400,'Use the notebook HTTPS trycloudflare.com service URL without a path or query.');
 const key=values.LOCAL_MUSIC_API_KEY??'';if(!key||key.length>512||/[^\x20-\x7e]/.test(key))error(400,'The public GPU tunnel requires its private connection key.');
 return {url:u.origin,key,version:uuid()};
}
async function boundedJSON(r){const text=await r.text();if(text.length>1000000)error(503,'The GPU returned an oversized response.');try{return JSON.parse(text)}catch{error(503,'The GPU returned an invalid response.')}}
async function gpu(config,path,data){
 let r;try{r=await fetch(config.url+path,{method:data?'POST':'GET',headers:{Authorization:'Bearer '+config.key,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,redirect:'manual',signal:AbortSignal.timeout(30000)})}catch{error(503,'Cannot reach your GPU. Keep Colab running and upload a fresh connection file. No song was fabricated.')}
 if(!r.ok){if([401,403].includes(r.status))error(503,'GPU authentication rejected. Upload a fresh notebook connection file.');error(503,'The GPU service is offline. Keep the notebook running and refresh its connection file. No song was fabricated.')}
 const result=await boundedJSON(r);if(result.code!==200||result.error)error(503,'The GPU rejected the request. Inspect its notebook log. No song was fabricated.');return result.data;
}
async function probe(config){const data=await gpu(config,'/query_result',{task_id_list:[]});if(!Array.isArray(data)||data.length)error(503,'Unexpected GPU readiness response.');return {authenticated:true,liveAudioVerified:false,listeningVerified:false,note:'Authenticated API check passed; generation and listening are unverified.'}}
function musicRequest(song){const s=song.settings;return {prompt:`Original ${s.genre} educational song, ${s.mood} mood, ${s.vocal} sung vocals in ${song.language==='hi'?'Hindi':'English'}, expressive melody, drums, bass, instruments and catchy repeated chorus. Sing the reviewed lyrics, not narration. Formula repetition preference: ${s.formulaRepeats}. ${s.instructions}`,lyrics:song.lyrics,vocal_language:song.language,bpm:s.tempo,audio_duration:s.length,key_scale:'C Major',time_signature:'4',task_type:'text2music',audio_format:'wav',batch_size:1,inference_steps:8,thinking:false,use_cot_caption:false,use_cot_language:false}}
async function listJSON(bucket,prefix,filter=()=>true){let cursor;const records=[];do{const result=await bucket.list({prefix,limit:500,...(cursor?{cursor}:{})});const batch=await Promise.all(result.objects.filter(o=>filter(o.key)).map(o=>readJSON(bucket,o.key)));records.push(...batch.filter(Boolean));cursor=result.truncated?result.cursor:null}while(cursor);return records}
function wavInfo(data){
 if(data.length<44)return false;const text=(a,n)=>String.fromCharCode(...data.slice(a,a+n));if(text(0,4)!=='RIFF'||text(8,4)!=='WAVE')return false;
 const view=new DataView(data.buffer,data.byteOffset,data.byteLength);let sampleRate=0,channels=0,bytesPerSec=0,dataLength=0;
 for(let i=12;i+8<=data.length;){const size=view.getUint32(i+4,true);if(text(i,4)==='fmt '&&size>=16&&i+24<=data.length){channels=view.getUint16(i+10,true);sampleRate=view.getUint32(i+12,true);bytesPerSec=view.getUint32(i+16,true)}if(text(i,4)==='data'){dataLength=Math.min(size,data.length-i-8);break}i+=8+size+(size%2)}
 return [1,2].includes(channels)&&sampleRate>0&&bytesPerSec>0&&dataLength/bytesPerSec>=1;
}
async function downloadGenerated(config,file){
 let p;try{p=new URL(file,config.url)}catch{error(503,'The GPU returned an invalid audio URL.')}
 if(p.pathname!=='/v1/audio'||p.hash)error(503,'The GPU returned an unexpected audio endpoint.');
 let r;try{r=await fetch(config.url+p.pathname+p.search,{headers:{Authorization:'Bearer '+config.key},redirect:'manual',signal:AbortSignal.timeout(60000)})}catch{error(503,'The GPU audio download failed. Keep the notebook open.')}
 if(!r.ok)error(503,'The GPU audio download failed. No audio was fabricated.');
 // Bounded stream avoids reading an untrusted arbitrarily large response.
 const reader=r.body.getReader(),parts=[];let length=0;
 while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>64000000){await reader.cancel();error(503,'The generated audio is too large. Request a shorter song.')}parts.push(value)}
 const data=new Uint8Array(length);let offset=0;for(const p of parts){data.set(p,offset);offset+=p.length}
 if(!wavInfo(data))error(503,'The GPU returned no usable WAV audio. No song was fabricated.');return data;
}

// Official ElevenLabs Music API only. No TTS, paid upgrades or credit purchases.
async function elevenFetch(key,path,body){
 let r;try{r=await fetch('https://api.elevenlabs.io/v1/'+path,{method:body?'POST':'GET',headers:{'xi-api-key':key,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,redirect:'manual',signal:AbortSignal.timeout(body?180000:30000)})}catch{error(503,'ElevenLabs could not be reached. No automatic retry or payment was made.')}
 if(!r.ok){if(r.status===401)error(503,'ElevenLabs rejected the API key or its permissions.');if([402,403].includes(r.status))error(503,'ElevenLabs blocked Music API access for this account. Its official Music API currently requires a paid subscription. No upgrade or payment was made.');if(r.status===429)error(503,'ElevenLabs quota or rate limit reached. No audio was generated.');error(503,'ElevenLabs music request failed (HTTP '+r.status+'). No audio was fabricated.')}
 return r;
}
function elevenPlan(song){
 const s=song.settings;let parts=song.lyrics.split(/\n(?=\[)/).filter(t=>t.trim());if(!parts.length)error(400,'Save reviewed lyrics first.');
 while(parts.length<Math.ceil(s.length/120)){const at=parts.findIndex(p=>p.split('\n').length>2);if(at<0)error(400,'Add more lyric sections or select a shorter song.');const lines=parts[at].split('\n'),mid=Math.ceil(lines.length/2);parts.splice(at,1,lines.slice(0,mid).join('\n'),lines.slice(mid).join('\n'))}
 if(parts.length>30||s.length*1000<parts.length*3000)error(400,'Choose a longer duration or fewer lyric sections (each needs at least 3 seconds).');
 const duration=Math.floor(s.length*1000/parts.length);return {model_id:'music_v2_5',composition_plan:{chunks:parts.map((text,i)=>({text,duration_ms:duration+(i===parts.length-1?s.length*1000-duration*parts.length:0),positive_styles:[s.genre,s.mood,s.vocal+' sung vocals','Clearly articulated '+(song.language==='hi'?'Hindi':'English')+' singing','expressive melody','drums bass and instrumental accompaniment','catchy chorus',s.tempo+' BPM',s.instructions||'educational song'],negative_styles:['spoken narration','text to speech','instrumental only'],context_adherence:'high'}))}};
}
async function elevenGenerate(c,song,key){
 const account=await boundedJSON(await elevenFetch(key,'user/subscription'));
 // The user permits free resources only; reject paid-tier calls instead of charging.
 if(account.tier!=='free')error(503,'Free-only mode: this ElevenLabs account is not on the free tier. No music call was made.');
 const plan=elevenPlan(song);const r=await elevenFetch(key,'music?output_format=mp3_44100_128',plan);
 const reader=r.body.getReader(),parts=[];let size=0;while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>32000000){await reader.cancel();error(503,'ElevenLabs returned an oversized song.')}parts.push(value)}
 const audio=new Uint8Array(size);let offset=0;for(const part of parts){audio.set(part,offset);offset+=part.length}
 if(size<1000||!(audio[0]===255||String.fromCharCode(...audio.slice(0,3))==='ID3'))error(503,'ElevenLabs returned no valid MP3 audio.');
 const filename=c.songsRoot+song.id+'.mp3';await c.bucket.put(filename,audio,{httpMetadata:{contentType:'audio/mpeg'}});return {...song,status:'ready',audio:filename,mime:'audio/mpeg',audio_origin:'ElevenLabs Music v2.5',error:null};
}
async function refreshSong(c,song){
 if(song.status==='failed'&&song.task&&song.error==='The GPU returned no usable audio. No song was fabricated.'&&now()-song.taskStarted<1800)song={...song,status:'generating'};
 if(song.status!=='generating')return song;
 if(song.musicProvider==='elevenlabs'){if(now()-song.taskStarted<200)return song;const failed={...song,status:'failed',error:'ElevenLabs request timed out before audio was saved. Check the provider dashboard before retrying.'};await saveJSON(c.bucket,c.songsRoot+song.id+'.json',failed);return failed;}
 let stage='connection';
 try{
  if(now()-song.taskStarted>1800)error(503,'GPU generation exceeded 30 minutes. Inspect the notebook before retrying.');
  const config=await readJSON(c.bucket,c.root+'music-connection');if(!config||config.version!==song.gpuVersion)error(503,'The GPU connection changed. Reconnect and synthesize again.');
  stage='task status';
  const rows=await gpu(config,'/query_result',{task_id_list:[song.task]});if(!Array.isArray(rows))error(503,'Invalid GPU task response.');
  const row=rows.find(r=>r&&r.task_id===song.task);if(!row)return song;
  if(Number(row.status)===2)error(503,'The GPU could not generate this song. Inspect its notebook log. No song was fabricated.');
  if(Number(row.status)===1){
   stage='result parsing';
   let outputs;try{outputs=typeof row.result==='string'?JSON.parse(row.result):row.result}catch{error(503,'The GPU returned an invalid audio result.')}
   const output=Array.isArray(outputs)?outputs[0]:outputs;if(!output?.file)error(503,'The GPU did not return an audio file.');
   stage='audio download';
   const audio=await downloadGenerated(config,output.file);const key=c.songsRoot+song.id+'.wav';
   stage='audio storage';
   await c.bucket.put(key,audio,{httpMetadata:{contentType:'audio/wav'}});
   song={...song,status:'ready',audio:key,mime:'audio/wav',audio_origin:'ACE-Step 1.5 connected GPU',error:null,provider_lyrics:typeof output.lyrics==='string'?output.lyrics.slice(0,16000):''};
   delete song.task;delete song.gpuVersion;
   await saveJSON(c.bucket,c.songsRoot+song.id+'.json',song);
  }
 }catch(e){console.error(JSON.stringify({event:'song_pipeline_failure',stage,errorType:String(e?.name||'Error'),detail:String(e?.message||'').replace(/https?:\/\/[^\s]+/g,'[service URL]').replace(/Bearer\s+[^\s]+/gi,'[credential]').slice(0,180)}));song={...song,status:'failed',audio:null,audio_origin:null,error:e instanceof APIError?e.message:`Song generation failed during ${stage} (${String(e?.name||'Error').replace(/[^a-zA-Z]/g,'')}). Retry synthesis; your lyrics are saved.`};await saveJSON(c.bucket,c.songsRoot+song.id+'.json',song)}
 return song;
}
async function songs(c,refresh=true){const rows=await listJSON(c.bucket,c.songsRoot,key=>key.endsWith('.json'));const jsonRows=rows.filter(s=>s.id);return (refresh?await Promise.all(jsonRows.map(s=>refreshSong(c,s))):jsonRows).sort((a,b)=>b.created-a.created)}
async function newDraft(c,id,lang,body={}){const t=topic(id);language(lang);const value={id:uuid(),sap:c.session.sap,topic:id,language:lang,title:t.title,lyrics:CONTENT.lessons[id].lyrics[lang],settings:settings(body),provenance:body.mode==='demo'?'Offline template; supplemental; no audio':'Local source-linked template; supplemental; no LLM',status:'draft',audio:null,mime:null,error:null,audio_origin:null,provider_lyrics:null,source_hash:CONTENT.lessons[id].hash,created:now()};await saveJSON(c.bucket,c.songsRoot+value.id+'.json',value);return value}
async function fileResponse(request,data,mime,name,download=false){
 const bytes=data instanceof Uint8Array?data:new Uint8Array(data);const headers={...HEADERS,'Content-Type':mime,'Accept-Ranges':'bytes'};
 if(download)headers['Content-Disposition']='attachment; filename="'+name.replace(/[^a-zA-Z0-9._-]/g,'_')+'"';
 const range=request.headers.get('Range');let start=0,end=bytes.length-1,status=200;
 if(range){const match=/^bytes=(\d*)-(\d*)$/.exec(range);if(!match||!match[1]&&!match[2])error(416,'Unsupported byte range.');start=match[1]?Number(match[1]):Math.max(0,bytes.length-Number(match[2]));end=match[1]&&match[2]?Math.min(Number(match[2]),bytes.length-1):bytes.length-1;if(start>end||start>=bytes.length)error(416,'Byte range outside file.');status=206;headers['Content-Range']=`bytes ${start}-${end}/${bytes.length}`}
 headers['Content-Length']=String(end-start+1);return new Response(bytes.slice(start,end+1),{status,headers});
}
async function dispatch(request,env){
 const url=new URL(request.url),path=decodeURIComponent(url.pathname);
 if(request.method==='GET'&&CONTENT.assets[path]){const asset=CONTENT.assets[path];return new Response(asset.text,{headers:{...HEADERS,'Content-Type':asset.mime}})}
 if(path==='/api/health')return response({ok:true,name:'Syllabus to Song',hosting:'Sites'});
 if(!path.startsWith('/api/'))error(404,'Page not found.');
 const bucket=env.BUCKET;if(!bucket)error(503,'Hosted persistent storage is not configured.');
 const visitor=request.headers.get('oai-authenticated-user-id');if(!visitor)error(401,'Open this private website while signed in with your ChatGPT account.');
 const root='users/'+await sha(visitor)+'/';const c={bucket,root};let body={};
 if(request.method==='POST'){
  const origin=request.headers.get('Origin');if(origin&&origin!==url.origin||request.headers.get('Sec-Fetch-Site')==='cross-site')error(403,'Cross-origin requests are not allowed.');
  if(Number(request.headers.get('Content-Length')||0)>22000000)error(413,'Upload too large.');
  const text=await request.text();if(text.length>22000000)error(413,'Upload too large.');
  try{body=JSON.parse(text)}catch{error(400,'A valid JSON request body is required.')}
  if(!body||typeof body!=='object'||Array.isArray(body))error(400,'A JSON object is required.');
 }
 if(path==='/api/login'&&request.method==='POST'){
  const sap=String(body.sap??'').trim(),password=String(body.password??'');if(!/^[a-zA-Z0-9_-]{3,30}$/.test(sap)||!password||password.length>200)error(400,'Enter a SAP ID and any nonempty sample password.');
  const role=sap===(env.ADMIN_SAP_ID||'admin')?'admin':'student';if(role==='admin'&&password!==(env.ADMIN_PASSWORD||'demo-admin'))error(401,'Incorrect administrator password.');
  const token=uuid()+uuid();const session={sap,role,expires:now()+86400};await saveJSON(bucket,root+'sessions/'+await sha(token),session);
  const current={...c,session,songsRoot:root+'songs/'+sap+'/'};
  if(sap==='70572400001'&&!(await songs(current,false)).length)for(const id of ['calc-01','beee-01'])for(const lang of ['en','hi'])await newDraft(current,id,lang,{mode:'demo'});
  return response({sap,role,sampleLogin:true},200,{'Set-Cookie':`session=${token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=86400`});
 }
 const token=/(?:^|;\s*)session=([^;]+)/.exec(request.headers.get('Cookie')||'')?.[1];if(!token)error(401,'Please sign in with your SAP ID.');
 const sessionKey=root+'sessions/'+await sha(token);c.session=await readJSON(bucket,sessionKey);if(!c.session||c.session.expires<now())error(401,'Session expired. Please sign in again.');
 c.songsRoot=root+'songs/'+c.session.sap+'/';const admin=()=>{if(c.session.role!=='admin')error(403,'Administrator login required.')};
 const musicConfig=()=>readJSON(bucket,root+'music-connection');
 if(request.method==='GET'){
  if(path==='/api/me')return response({sap:c.session.sap,role:c.session.role});
  if(path==='/api/catalogue')return response(CONTENT.catalogue);
  if(path==='/api/providers'){
   const config=await musicConfig(),all=await songs(c,false),eleven=await readJSON(bucket,root+'elevenlabs');return response({elevenlabs:{configured:!!eleven,tier:eleven?.tier||null,musicAccessVerified:all.some(s=>s.status==='ready'&&s.audio_origin==='ElevenLabs Music v2.5')},configured:!!config,backend:'gpu',mode:config?'GPU connection configured':'free GPU connection required',lyricsModel:'Local source-linked templates (editable; no LLM)',musicModel:'acestep-v15-turbo',check:await readJSON(bucket,root+'provider-check'),liveAudioVerified:all.some(s=>s.status==='ready'&&s.audio_origin==='ACE-Step 1.5 connected GPU'),blocker:config?null:'Connect your free Colab GPU in Connections to enable AI singing. No song has been fabricated. This hosted website cannot run a multi-gigabyte CPU model.',capabilities:'Native BPM, duration, English/Hindi language and exact saved lyrics. Genre, mood, voice and repetition are preferences. No paid API; keep your free GPU notebook running.'});
  }
  if(path==='/api/songs')return response((await songs(c)).map(publicSong));
  if(path==='/api/attempts')return response((await listJSON(bucket,root+'attempts/'+c.session.sap+'/')).sort((a,b)=>b.created-a.created));
  const lesson=/^\/api\/topics\/([^/]+)(\/quiz)?$/.exec(path);
  if(lesson){const t=topic(lesson[1]),lang=language(url.searchParams.get('language')||'en');if(lesson[2])return response({questions:CONTENT.lessons[t.id].quiz[lang].map(({correct,explanation,...q})=>q),provenance:'Supplemental source-derived revision quiz; not an official examination'});const uploads=(await listJSON(bucket,root+'uploads/')).filter(u=>u.topic===t.id&&u.approved);return response({...t,supplemental:CONTENT.lessons[t.id].supplemental,uploads})}
  if(path==='/api/admin/uploads'){admin();return response((await listJSON(bucket,root+'uploads/')).sort((a,b)=>b.created-a.created))}
  if(path.startsWith('/api/sources/')){const name=path.slice('/api/sources/'.length),source=CONTENT.sources[name];if(!source)error(404,'Source not found.');return fileResponse(request,b64bytes(source.data),source.mime,name,true)}
  if(['/api/coverage','/api/coverage.csv'].includes(path)){
   const all=await songs(c);const report=CONTENT.catalogue.topics.map(t=>{const entries=all.filter(s=>s.topic===t.id);return {id:t.id,subject:t.subject,unit:t.unit,chapter:t.chapter,topic:t.title,content:'Uploaded summary; full notes pending',hindi:'Supplemental explanation available',lyrics_en:entries.some(s=>s.language==='en')?'Saved draft':'Offline template available; not saved',lyrics_hi:entries.some(s=>s.language==='hi')?'Saved draft':'Offline template available; not saved',quiz:'2 supplemental revision questions ready',audio:entries.some(s=>s.status==='ready')?'Ready':'Not generated',source:t.source,locator:t.locator}});
   if(path.endsWith('.csv')){const fields=Object.keys(report[0]),cell=v=>'"'+String(v??'').replaceAll('"','""')+'"';const csv='\ufeff'+[fields,...report.map(r=>fields.map(f=>r[f]))].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';return new Response(csv,{headers:{...HEADERS,'Content-Type':'text/csv; charset=utf-8','Content-Disposition':'attachment; filename="syllabus-completeness.csv"'}})}
   return response({topics:report,indexed:91,fullNotesReady:0,note:'All uploaded headings are indexed. Audio readiness and full notes are tracked separately.'});
  }
  const audio=/^\/api\/songs\/([a-f0-9-]+)\/audio$/.exec(path);if(audio){const s=await readJSON(bucket,c.songsRoot+audio[1]+'.json');if(!s?.audio)error(404,'No audio exists for this song.');const file=await bucket.get(s.audio);if(!file)error(404,'Audio file not found.');return fileResponse(request,await file.arrayBuffer(),s.mime,audio[1]+(s.mime.includes('wav')?'.wav':'.mp3'),url.searchParams.has('download'))}
 }
 if(request.method==='POST'){
  if(path==='/api/logout'){await bucket.delete(sessionKey);return response({ok:true},200,{'Set-Cookie':'session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0'})}
  if(path==='/api/admin/elevenlabs'){
   admin();if(body.disconnect===true){await bucket.delete(root+'elevenlabs');return response({configured:false})}
   const key=body.apiKey;if(typeof key!=='string'||key.length<10||key.length>512||/[^\x21-\x7e]/.test(key))error(400,'Enter a valid private ElevenLabs API key.');
   const account=await boundedJSON(await elevenFetch(key,'user/subscription'));if(typeof account.tier!=='string')error(503,'ElevenLabs returned an unknown subscription response.');
   await saveJSON(bucket,root+'elevenlabs',{key,tier:account.tier});return response({configured:true,tier:account.tier,musicAccessVerified:false,note:'Key authenticated. Music API permission remains unverified; official access requires a paid plan. Free-only mode will not call paid-tier accounts.'});
  }
  if(path==='/api/admin/music-service'){
   admin();if((await listJSON(bucket,root+'songs/',key=>key.endsWith('.json'))).some(s=>s.status==='generating'))error(409,'Wait for the current song before changing the music connection.');
   if(body.local===true){await bucket.delete(root+'music-connection');await bucket.delete(root+'provider-check');return response({configured:false,liveAudioVerified:false,mode:'GPU disconnected'})}
   const config=validateConnection(body.configuration);const check={configured:true,provider:'ACE-Step 1.5 connected GPU',musicModel:'acestep-v15-turbo',...await probe(config)};await saveJSON(bucket,root+'music-connection',config);await saveJSON(bucket,root+'provider-check',check);return response(check);
  }
  if(path==='/api/providers/check'){admin();const config=await musicConfig();const check=config?{configured:true,provider:'ACE-Step 1.5 connected GPU',...await probe(config)}:{configured:false,liveAudioVerified:false,listeningVerified:false,checks:[{status:'blocked',reason:'No free GPU is connected. Upload song-service.env from your running notebook.'}]};await saveJSON(bucket,root+'provider-check',check);return response(check)}
  if(path==='/api/lyrics'){if(!['free','live','demo'].includes(body.mode??'free'))error(400,'Choose free source-linked drafting or the offline template.');return response(publicSong(await newDraft(c,body.topic,language(body.language),body)),201)}
  const match=/^\/api\/songs\/([a-f0-9-]+)\/(save|synthesize|upload-audio)$/.exec(path);
  if(match){
   const key=c.songsRoot+match[1]+'.json';let s=await readJSON(bucket,key);if(!s)error(404,'Song not found.');s=await refreshSong(c,s);if(s.status==='generating')error(409,'This song is already generating. Wait for it to finish.');
   if(match[2]==='save'){
    if(typeof body.lyrics!=='string'||!body.lyrics.trim()||body.lyrics.length>16000)error(400,'Lyrics must contain 1–16000 characters.');const next=body.settings?settings(body):s.settings;
    if(body.lyrics!==s.lyrics||JSON.stringify(next)!==JSON.stringify(s.settings)){s={...s,lyrics:body.lyrics,settings:next,status:'draft',audio:null,mime:null,provider_lyrics:null,audio_origin:null,error:null}}
   }
   if(match[2]==='synthesize'){
    if(body.provider==='elevenlabs'){
     const config=await readJSON(bucket,root+'elevenlabs');if(!config)error(503,'Connect an ElevenLabs API key in section 2 first.');
     const claimed=await bucket.get(key);const pending={...s,status:'generating',musicProvider:'elevenlabs',taskStarted:now(),error:null};const claim=await bucket.put(key,JSON.stringify(pending),{onlyIf:{etagMatches:claimed.etag},httpMetadata:{contentType:'application/json'}});if(!claim)error(409,'Another request changed this song. Refresh first.');
     try{s=await elevenGenerate(c,pending,config.key)}catch(e){s={...s,status:'failed',audio:null,error:e instanceof APIError?e.message:'ElevenLabs generation failed before usable audio was saved.'};await saveJSON(bucket,key,s);throw e}
     await saveJSON(bucket,key,s);return response(publicSong(s));
    }
    const config=await musicConfig();if(!config)error(503,'Connect your free Colab GPU in Connections first. No song was fabricated.');
    if((await songs(c,false)).some(v=>v.status==='generating'))error(409,'The free GPU is already generating a song. Wait for it to finish.');
    const result=await gpu(config,'/release_task',musicRequest(s));if(typeof result?.task_id!=='string'||result.task_id.length>200)error(503,'The GPU returned no task ID.');
    s={...s,status:'generating',error:null,audio:null,audio_origin:null,task:result.task_id,taskStarted:now(),gpuVersion:config.version};
   }
   if(match[2]==='upload-audio'){
    if(body.permitted!==true)error(400,'Confirm you have permission to use and download this audio.');let data;try{data=b64bytes(body.data)}catch{error(400,'Invalid audio encoding.')}
    if(data.length<40||data.length>16000000)error(400,'Audio must be between 40 bytes and 16 MB.');const tag=String.fromCharCode(...data.slice(0,12));const wav=body.mime==='audio/wav'&&tag.startsWith('RIFF')&&tag.slice(8)==='WAVE',mp3=body.mime==='audio/mpeg'&&(tag.startsWith('ID3')||data[0]===255);if(!wav&&!mp3)error(400,'Use a valid WAV or MP3 audio file.');const audio=c.songsRoot+s.id+(wav?'.wav':'.mp3');await bucket.put(audio,data,{httpMetadata:{contentType:body.mime}});s={...s,status:'ready',audio,mime:body.mime,audio_origin:'User supplied audio; not generated by this app',error:null};
   }
   await saveJSON(bucket,key,s);return response(publicSong(s));
  }
  if(path==='/api/quiz/submit'){
   const t=topic(body.topic),lang=language(body.language),questions=CONTENT.lessons[t.id].quiz[lang],answers=body.answers;if(!Array.isArray(answers)||answers.length!==questions.length||answers.some(a=>!Number.isInteger(a)||a<0||a>3))error(400,'Answer every question before submitting.');const score=answers.filter((a,i)=>a===questions[i].correct).length;await saveJSON(bucket,root+'attempts/'+c.session.sap+'/'+uuid(),{topic:t.id,score,total:questions.length,created:now()});return response({score,total:questions.length,feedback:questions});
  }
  if(path==='/api/admin/uploads'){
   admin();topic(body.topic);const name=String(body.name??'').trim(),excerpt=String(body.excerpt??'').trim();if(!name||name.length>150||excerpt.length<10||excerpt.length>30000)error(400,'Enter a source name and a 10–30000 character academic excerpt.');let filename=null;
   if(body.data){if(!/\.(pdf|txt|md|csv)$/i.test(name))error(400,'Upload PDF, TXT, MD or CSV material.');let bytes;try{bytes=b64bytes(body.data)}catch{error(400,'Invalid upload encoding.')}if(bytes.length>16000000)error(413,'Maximum upload size is 16 MB.');filename=root+'material/'+uuid();await bucket.put(filename,bytes)}
   const id=uuid();await saveJSON(bucket,root+'uploads/'+id,{id,topic:body.topic,name,excerpt,filename,approved:false,created:now()});return response({id,approved:false,note:'Pending admin review; supplemental material after approval.'},201);
  }
  const approval=/^\/api\/admin\/uploads\/([a-f0-9-]+)\/approve$/.exec(path);if(approval){admin();const key=root+'uploads/'+approval[1],record=await readJSON(bucket,key);if(!record)error(404,'Upload not found.');await saveJSON(bucket,key,{...record,approved:true});return response({approved:true,label:'Admin-approved supplemental material; not an official syllabus change'})}
 }
 error(404,'API route not found.');
}
export default {async fetch(request,env,ctx){try{return await dispatch(request,env)}catch(e){return response({error:e instanceof APIError?e.message:'The server could not complete this request. Please retry.'},e instanceof APIError?e.status:500)}}};
