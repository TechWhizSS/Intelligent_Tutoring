package com.nmims.songstudio.data

import android.content.Context
import android.media.MediaMetadataRetriever
import com.nmims.songstudio.playback.AudioFiles
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

/**
 * Bridges persistent storage (SQLite) and on-disk audio files.
 * All public methods are suspend or return Flow and are safe to call from coroutines.
 */
class SongRepository(private val context: Context, private val dao: SongDao) {

    fun history(studentId: Long): Flow<List<SongRecord>> = dao.historyFlow(studentId)
    fun saved(studentId: Long): Flow<List<SongRecord>> = dao.savedFlow(studentId)

    /** Persist a generation result. Returns the record (new or existing). */
    suspend fun recordGeneration(
        studentId: Long,
        subject: String,
        unit: String,
        topicTitle: String,
        topicId: Int,
        songTitle: String,
        referenceTitle: String,
        language: String,
        category: String,
        styleName: String,
        lyrics: String,
        audioFileKey: String,
        generationMode: String
    ): SongRecord = withContext(Dispatchers.IO) {
        val duration = extractDuration(audioFileKey)
        val existing = dao.findByKey(studentId, audioFileKey)
        if (existing != null) {
            // Update lyrics/duration if changed, but don't create a duplicate.
            val updated = existing.copy(
                lyrics = lyrics,
                durationMs = if (duration > 0) duration else existing.durationMs
            )
            if (updated != existing) {
                dao.update(updated)
            }
            return@withContext updated
        }
        val record = SongRecord(
            studentId = studentId,
            subject = subject,
            unit = unit,
            topicTitle = topicTitle,
            topicId = topicId,
            songTitle = songTitle,
            referenceTitle = referenceTitle,
            language = language,
            category = category,
            styleName = styleName,
            lyrics = lyrics,
            audioFileKey = audioFileKey,
            generationMode = generationMode,
            durationMs = duration
        )
        val id = dao.insert(record)
        if (id > 0) record.copy(id = id) else dao.findByKey(studentId, audioFileKey) ?: record
    }

    suspend fun toggleSaved(record: SongRecord): SongRecord = withContext(Dispatchers.IO) {
        val newSaved = !record.saved
        dao.setSaved(record.id, record.studentId, newSaved)
        record.copy(saved = newSaved)
    }

    suspend fun findById(id: Long, studentId: Long): SongRecord? = dao.findById(id, studentId)

    /** Delete the record and its audio file (if no other record references the same key). */
    suspend fun deleteRecord(record: SongRecord) = withContext(Dispatchers.IO) {
        dao.delete(record)
        // Only delete audio if no other record references this key.
        val remaining = dao.countByKey(record.audioFileKey)
        if (remaining == 0) {
            val file = AudioFiles.file(context, record.audioFileKey)
            file.delete()
            file.resolveSibling(file.name + ".mode").delete()
        }
    }

    suspend fun clearUnsavedHistory(studentId: Long) = withContext(Dispatchers.IO) {
        dao.clearUnsavedHistory(studentId)
    }

    /** Check whether the audio file still exists on disk. */
    fun audioExists(record: SongRecord): Boolean =
        AudioFiles.file(context, record.audioFileKey).exists()

    fun audioFile(record: SongRecord) = AudioFiles.file(context, record.audioFileKey)

    private fun extractDuration(audioFileKey: String): Long {
        val file = AudioFiles.file(context, audioFileKey)
        if (!file.exists() || file.length() < 100) return 0
        return try {
            val retriever = MediaMetadataRetriever()
            try {
                retriever.setDataSource(file.absolutePath)
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0
            } finally { retriever.release() }
        } catch (_: Exception) { 0 }
    }
}
