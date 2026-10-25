package com.nmims.songstudio

import com.nmims.songstudio.generation.AceProtocol
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class AceProtocolTest {
    @Test fun importsOnlySupportedConnectionValues() {
        val c=AceProtocol.fromFile("# private notebook export\nLOCAL_MUSIC_URL=https://sample-gpu.trycloudflare.com\nLOCAL_MUSIC_API_KEY=test-only-private-key")
        assertEquals("https://sample-gpu.trycloudflare.com",c.origin)
        assertEquals("test-only-private-key",c.key)
    }
    @Test fun refusesExecutableOrUnrelatedConfiguration() {
        for(s in listOf("RUN=echo hello","LOCAL_MUSIC_URL=http://example.com\nLOCAL_MUSIC_API_KEY=abc","LOCAL_MUSIC_URL=https://example.com/private\nLOCAL_MUSIC_API_KEY=abc","LOCAL_MUSIC_URL=https://user:pass@example.com\nLOCAL_MUSIC_API_KEY=abc")) {
            assertThrows(IllegalArgumentException::class.java){AceProtocol.fromFile(s)}
        }
    }
    @Test fun requiresPublicConnectionKey() {
        assertThrows(IllegalArgumentException::class.java){AceProtocol.connection("https://sample-gpu.trycloudflare.com","")}
        assertThrows(IllegalArgumentException::class.java){AceProtocol.connection("https://example.com","bad\nheader")}
        assertEquals("http://10.0.2.2:8001",AceProtocol.connection("http://10.0.2.2:8001","").origin)
    }
    @Test fun handlesAllOfficialResultShapes() {
        val item=JSONObject().put("file","/v1/audio?path=real.wav")
        for(value in listOf(item,JSONArray().put(item),item.toString(),JSONArray().put(item).toString()))assertEquals("/v1/audio?path=real.wav",AceProtocol.output(value))
        assertThrows(IllegalStateException::class.java){AceProtocol.output(JSONArray())}
    }
    @Test fun downloadsOnlyExpectedPathFromConfiguredOrigin() {
        assertEquals("/v1/audio?path=real.wav",AceProtocol.audioPath("https://untrusted.example/v1/audio?path=real.wav"))
        for(value in listOf("/other/audio.wav","https://example.com/v1/audio#fragment","https://user:pass@example.com/v1/audio")) {
            assertThrows(IllegalArgumentException::class.java){AceProtocol.audioPath(value)}
        }
    }
    @Test fun acceptsBoundedTaskIdentifiers() {
        assertEquals("task-1",AceProtocol.task(JSONObject().put("task_id","task-1")))
        assertThrows(IllegalArgumentException::class.java){AceProtocol.task(JSONObject().put("task_id",""))}
    }
    @Test fun sendsExactReviewedLyricsAndNativeMusicFields() {
        val lyrics="[Verse]\nवी बराबर आई गुणा आर\n[Chorus]\nV = I R"
        for(language in listOf("en","hi")) {
            val body=AceProtocol.musicRequest(lyrics,language,com.nmims.songstudio.data.MusicSettings(tempo=120,seconds=60))
            assertEquals(lyrics,body.getString("lyrics"));assertEquals(language,body.getString("vocal_language"))
            assertEquals(120,body.getInt("bpm"));assertEquals(60,body.getInt("audio_duration"))
            assertEquals("text2music",body.getString("task_type"));assertEquals("wav",body.getString("audio_format"))
            assertFalse(body.getBoolean("thinking"))
        }
        assertThrows(IllegalArgumentException::class.java){AceProtocol.musicRequest(lyrics,"unsupported",com.nmims.songstudio.data.MusicSettings())}
    }

}
