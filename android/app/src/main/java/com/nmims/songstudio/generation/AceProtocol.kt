package com.nmims.songstudio.generation

import com.nmims.songstudio.data.MusicSettings
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI

data class AceConnection(val origin:String,val key:String)
/** Pure request/response rules, shared by the device client and JVM tests. */
object AceProtocol {
    fun connection(origin:String,key:String):AceConnection {
        val uri=runCatching { URI(origin.trim().trimEnd('/')) }.getOrElse { error("Enter a valid HTTPS GPU address.") }
        val local=uri.scheme=="http" && uri.host in listOf("localhost","127.0.0.1","10.0.2.2") && uri.port==8001
        require((uri.scheme=="https"&&uri.host!=null&&uri.port in listOf(-1,443)||local)&&uri.userInfo==null&&uri.rawPath.orEmpty().isEmpty()&&uri.rawQuery==null&&uri.rawFragment==null) { "Use an HTTPS GPU origin without a path, query or embedded credentials. Emulator development may use http://10.0.2.2:8001." }
        require(key.length<=512&&key.all { it.code in 33..126 }&&(local||key.isNotBlank())) { "The GPU requires its private connection key." }
        return AceConnection(uri.toString(),key)
    }
    fun fromFile(text:String):AceConnection {
        require(text.length<=8192) { "Choose the small song-service.env file." }
        val values=mutableMapOf<String,String>()
        text.lineSequence().map { it.trim() }.filter { it.isNotEmpty()&&!it.startsWith("#") }.forEach { line ->
            val at=line.indexOf('=');require(at>0) { "Invalid connection file." };val name=line.substring(0,at).trim()
            require(name in listOf("LOCAL_MUSIC_URL","LOCAL_MUSIC_API_KEY")) { "Unsupported connection file. It is read as data, never executed." }
            values[name]=line.substring(at+1).trim().trim('"','\'')
        }
        return connection(values["LOCAL_MUSIC_URL"].orEmpty(),values["LOCAL_MUSIC_API_KEY"].orEmpty())
    }
    fun musicRequest(lyrics:String,language:String,settings:MusicSettings):JSONObject {
        require(language in listOf("en","hi"));require(lyrics.isNotBlank()&&lyrics.length<=16000)
        require(settings.tempo in 60..180&&settings.seconds in 30..240&&settings.repeats in 1..4)
        return JSONObject().put("prompt",settings.caption(language)).put("lyrics",lyrics).put("vocal_language",language)
            .put("bpm",settings.tempo).put("audio_duration",settings.seconds).put("task_type","text2music")
            .put("audio_format","wav").put("batch_size",1).put("inference_steps",8).put("thinking",false)
            .put("use_cot_caption",false).put("use_cot_language",false).put("key_scale","C Major").put("time_signature","4")
    }
    fun task(body:JSONObject):String {
        val id=body.getString("task_id");require(id.isNotBlank()&&id.length<=200);return id
    }
    fun output(value:Any?):String {
        val decoded=if(value is String)org.json.JSONTokener(value).nextValue() else value
        val item=if(decoded is JSONArray)decoded.optJSONObject(0) else decoded as? JSONObject
        return item?.optString("file")?.takeIf { it.isNotBlank() } ?: error("GPU returned no audio file. Check the notebook log.")
    }
    fun audioPath(file:String):String {
        val uri=URI(file);require(uri.rawPath=="/v1/audio"&&uri.rawFragment==null&&uri.rawUserInfo==null) { "Unexpected audio endpoint from GPU." }
        // Always download from the saved origin, never a provider-supplied host.
        return uri.rawPath+(uri.rawQuery?.let { "?$it" } ?: "")
    }
}
