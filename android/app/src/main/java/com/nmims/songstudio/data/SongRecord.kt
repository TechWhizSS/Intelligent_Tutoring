package com.nmims.songstudio.data

/**
 * Persistent record of every successfully generated song.
 * Uses the audio file key (the SHA-256 hash input to AudioFiles) as the storage reference
 * instead of fragile absolute paths.
 *
 * Implemented as a clean Kotlin data class without Room annotations, compatible with
 * Android's built-in SQLiteOpenHelper.
 */
data class SongRecord(
    val id: Long = 0,
    val studentId: Long,
    val subject: String,
    val unit: String,
    val topicTitle: String,
    val topicId: Int,
    val songTitle: String,
    val referenceTitle: String,
    val language: String,
    val category: String,
    val styleName: String,
    val lyrics: String,
    val audioFileKey: String,
    val generationMode: String,
    val createdAt: Long = System.currentTimeMillis(),
    val saved: Boolean = false,
    val durationMs: Long = 0
)
