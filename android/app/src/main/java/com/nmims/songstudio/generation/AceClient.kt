package com.nmims.songstudio.generation

import android.content.Context
import android.media.MediaMetadataRetriever
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.nmims.songstudio.data.MusicSettings
import com.nmims.songstudio.playback.AudioFiles
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Phone → owner's official ACE-Step API. No emulator bridge or paid API. */
class AceClient(private val context:Context) {
    private val prefs=context.getSharedPreferences("ace-connection",Context.MODE_PRIVATE)
    private fun secret():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("ace-gpu-key",null) as? SecretKey)?.let {return it}
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("ace-gpu-key",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun saved():AceConnection? {
        val origin=prefs.getString("origin",null) ?: return null
        return runCatching {
            val iv=Base64.decode(prefs.getString("iv",""),Base64.NO_WRAP)
            val cipher=Cipher.getInstance("AES/GCM/NoPadding").apply {init(Cipher.DECRYPT_MODE,secret(),GCMParameterSpec(128,iv))}
            val key=String(cipher.doFinal(Base64.decode(prefs.getString("key",""),Base64.NO_WRAP)))
            AceProtocol.connection(origin,key)
        }.getOrNull()
    }
    fun save(config:AceConnection) {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding").apply {init(Cipher.ENCRYPT_MODE,secret())}
        prefs.edit().putString("origin",config.origin).putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP))
            .putString("key",Base64.encodeToString(cipher.doFinal(config.key.toByteArray()),Base64.NO_WRAP)).apply()
    }
    fun disconnect(){prefs.edit().clear().apply()}
    private fun open(c:AceConnection,path:String):HttpURLConnection=(URL(c.origin+path).openConnection() as HttpURLConnection).apply {
        connectTimeout=15000;readTimeout=30000;instanceFollowRedirects=false
        if(c.key.isNotEmpty())setRequestProperty("Authorization","Bearer "+c.key)
    }
    private fun request(c:AceConnection,path:String,body:JSONObject):Any {
        val connection=open(c,path)
        try {
            connection.requestMethod="POST";connection.doOutput=true;connection.setRequestProperty("Content-Type","application/json")
            connection.outputStream.use { it.write(body.toString().toByteArray()) }
            val code=connection.responseCode
            check(code in 200..299) {if(code in listOf(401,403))"GPU rejected the private connection key. Import a fresh connection file." else "GPU request failed (HTTP $code). Keep the notebook running."}
            val bytes=connection.inputStream.use { input -> val output=java.io.ByteArrayOutputStream();val buffer=ByteArray(8192);while(true){val n=input.read(buffer);if(n<0)break;check(output.size()+n<=1_000_000){"GPU response too large."};output.write(buffer,0,n)};output.toByteArray() }
            val result=JSONObject(String(bytes));check(result.optInt("code")==200&&(result.isNull("error")||result.optString("error").isEmpty())) {"GPU rejected this task. Check its notebook log."}
            return result.get("data")
        }finally{connection.disconnect()}
    }
    suspend fun probe(c:AceConnection)=withContext(Dispatchers.IO) {
        val rows=request(c,"/query_result",JSONObject().put("task_id_list",JSONArray()))
        check(rows is JSONArray && rows.length()==0) {"Unexpected official ACE-Step readiness response."}
    }
    suspend fun generate(key:String,lyrics:String,language:String,settings:MusicSettings,onStatus:(String)->Unit):File=withContext(Dispatchers.IO) {
        require(language in listOf("en","hi"));require(lyrics.isNotBlank()&&lyrics.length<=16000)
        val config=saved() ?: error("Connect your GPU in Settings, or use the Gemini button.")
        val body=AceProtocol.musicRequest(lyrics,language,settings)
        val task=AceProtocol.task(request(config,"/release_task",body) as JSONObject)
        onStatus("GPU accepted the task. Composing vocals and instruments…")
        withTimeout(1_800_000L) {
            while(true) {
                ensureActive();delay(2500)
                val rows=request(config,"/query_result",JSONObject().put("task_id_list",JSONArray().put(task))) as JSONArray
                val row=(0 until rows.length()).map { rows.getJSONObject(it) }.firstOrNull { it.optString("task_id")==task } ?: continue
                when(row.optInt("status")) {
                    2 -> error("The GPU could not generate this song. Check its notebook log. No audio was substituted.")
                    1 -> {
                        val path=AceProtocol.audioPath(AceProtocol.output(row.opt("result")))
                        val target=AudioFiles.file(context,key);val temporary=File.createTempFile("ace-",".wav",target.parentFile)
                        val connection=open(config,path)
                        try {
                            connection.readTimeout=60000;check(connection.responseCode==200) {"GPU audio download failed."}
                            connection.inputStream.use { input -> temporary.outputStream().use { output ->
                                val buffer=ByteArray(8192);var length=0L
                                while(true){ensureActive();val n=input.read(buffer);if(n<0)break;length+=n;check(length<=64_000_000){"GPU audio is too large."};output.write(buffer,0,n)}
                            } }
                            val header=ByteArray(12);java.io.DataInputStream(temporary.inputStream()).use { it.readFully(header) }
                            check(header.size==12&&String(header,0,4)=="RIFF"&&String(header,8,4)=="WAVE") {"GPU returned no valid WAV audio."}
                            val metadata=MediaMetadataRetriever()
                            try{metadata.setDataSource(temporary.absolutePath);check((metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0)>=1000){"GPU returned unusable audio."}}finally{metadata.release()}
                            check(temporary.renameTo(target)){"Could not save the actual GPU song."}
                            target.resolveSibling(target.name+".mode").writeText("ACE-Step 1.5 GPU; listening review required")
                            return@withTimeout target
                        }finally{connection.disconnect();temporary.delete()}
                    }
                }
            }
            @Suppress("UNREACHABLE_CODE") error("Generation did not complete.")
        }
    }
}
