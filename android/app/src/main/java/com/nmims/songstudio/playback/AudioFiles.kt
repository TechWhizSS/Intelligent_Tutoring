package com.nmims.songstudio.playback

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import java.io.File
import java.security.MessageDigest

/** App-private, selection-specific audio. No uploads or access to unrelated files. */
object AudioFiles {
    fun file(context: Context, key: String): File {
        val digest = MessageDigest.getInstance("SHA-256").digest(key.toByteArray())
            .joinToString("") { "%02x".format(it) }
        return File(File(context.filesDir, "songs").apply { mkdirs() }, "$digest.audio")
    }

    fun import(context: Context, uri: Uri, key: String) {
        val target = file(context, key)
        val temporary = File.createTempFile("import-", ".audio", target.parentFile)
        try {
            val input = context.contentResolver.openInputStream(uri) ?: error("The selected file cannot be opened.")
            input.use { source -> temporary.outputStream().use { output ->
                val buffer = ByteArray(8192)
                var total = 0L
                while (true) {
                    val n = source.read(buffer)
                    if (n < 0) break
                    total += n
                    require(total <= 50L * 1024 * 1024) { "Choose an audio file smaller than 50 MB." }
                    output.write(buffer, 0, n)
                }
            } }
            val metadata = MediaMetadataRetriever()
            try {
                metadata.setDataSource(temporary.absolutePath)
                val duration = metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0
                require(duration > 0) { "Choose a playable MP3, WAV or M4A file." }
                require(metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_AUDIO) == "yes") { "The selected file contains no audio." }
            } finally { metadata.release() }
            check(temporary.renameTo(target)) { "The song could not be saved. Please try again." }
        } finally { temporary.delete() }
    }
}
