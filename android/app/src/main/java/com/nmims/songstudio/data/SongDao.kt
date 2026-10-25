package com.nmims.songstudio.data

import android.content.ContentValues
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext

/**
 * Data Access Object interface for persisted song records.
 * Provides Flow-based reactive queries for UI observation and suspend functions for writes.
 */
interface SongDao {
    /** All songs for the student ordered by most recent first. */
    fun historyFlow(studentId: Long): Flow<List<SongRecord>>

    /** Only saved/favourited songs for the student. */
    fun savedFlow(studentId: Long): Flow<List<SongRecord>>

    /** Single record lookup by audio key + student. */
    suspend fun findByKey(studentId: Long, audioFileKey: String): SongRecord?

    /** Single record lookup by database ID + student. */
    suspend fun findById(id: Long, studentId: Long): SongRecord?

    /** Total records referencing this audioFileKey across all students. */
    suspend fun countByKey(audioFileKey: String): Int

    /** Inserts record. Returns inserted row ID, or -1 if ignored due to unique conflict. */
    suspend fun insert(record: SongRecord): Long

    /** Update an existing record. */
    suspend fun update(record: SongRecord)

    /** Toggle or set saved state. */
    suspend fun setSaved(id: Long, studentId: Long, saved: Boolean)

    /** Update cached duration. */
    suspend fun setDuration(id: Long, durationMs: Long)

    /** Delete a record. */
    suspend fun delete(record: SongRecord)

    /** Remove all unsaved songs for this student. */
    suspend fun clearUnsavedHistory(studentId: Long)
}

/**
 * Android SQLiteOpenHelper-backed implementation of [SongDao].
 * Operates without Room or KSP dependencies using Android's built-in SQLite APIs.
 */
class SQLiteSongDao(private val dbHelper: SQLiteOpenHelper) : SongDao {

    // Monotonic trigger for notifying Flow collectors whenever the database is mutated.
    private val mutationTrigger = MutableStateFlow(0L)

    private fun notifyMutation() {
        mutationTrigger.value += 1
    }

    override fun historyFlow(studentId: Long): Flow<List<SongRecord>> =
        mutationTrigger.map {
            queryHistory(studentId)
        }.flowOn(Dispatchers.IO)

    override fun savedFlow(studentId: Long): Flow<List<SongRecord>> =
        mutationTrigger.map {
            querySaved(studentId)
        }.flowOn(Dispatchers.IO)

    private fun queryHistory(studentId: Long): List<SongRecord> {
        val db = dbHelper.readableDatabase
        val cursor = db.query(
            TABLE_NAME,
            null,
            "$COLUMN_STUDENT_ID = ?",
            arrayOf(studentId.toString()),
            null,
            null,
            "$COLUMN_CREATED_AT DESC"
        )
        return cursor.use { it.toSongRecordList() }
    }

    private fun querySaved(studentId: Long): List<SongRecord> {
        val db = dbHelper.readableDatabase
        val cursor = db.query(
            TABLE_NAME,
            null,
            "$COLUMN_STUDENT_ID = ? AND $COLUMN_SAVED = 1",
            arrayOf(studentId.toString()),
            null,
            null,
            "$COLUMN_CREATED_AT DESC"
        )
        return cursor.use { it.toSongRecordList() }
    }

    override suspend fun findByKey(studentId: Long, audioFileKey: String): SongRecord? =
        withContext(Dispatchers.IO) {
            val db = dbHelper.readableDatabase
            val cursor = db.query(
                TABLE_NAME,
                null,
                "$COLUMN_STUDENT_ID = ? AND $COLUMN_AUDIO_FILE_KEY = ?",
                arrayOf(studentId.toString(), audioFileKey),
                null,
                null,
                null,
                "1"
            )
            cursor.use {
                if (it.moveToFirst()) it.toSongRecord() else null
            }
        }

    override suspend fun findById(id: Long, studentId: Long): SongRecord? =
        withContext(Dispatchers.IO) {
            val db = dbHelper.readableDatabase
            val cursor = db.query(
                TABLE_NAME,
                null,
                "$COLUMN_ID = ? AND $COLUMN_STUDENT_ID = ?",
                arrayOf(id.toString(), studentId.toString()),
                null,
                null,
                null,
                "1"
            )
            cursor.use {
                if (it.moveToFirst()) it.toSongRecord() else null
            }
        }

    override suspend fun countByKey(audioFileKey: String): Int =
        withContext(Dispatchers.IO) {
            val db = dbHelper.readableDatabase
            val cursor = db.rawQuery(
                "SELECT COUNT(*) FROM $TABLE_NAME WHERE $COLUMN_AUDIO_FILE_KEY = ?",
                arrayOf(audioFileKey)
            )
            cursor.use {
                if (it.moveToFirst()) it.getInt(0) else 0
            }
        }

    override suspend fun insert(record: SongRecord): Long =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            val values = record.toContentValues(includeId = false)
            val insertedId = db.insertWithOnConflict(
                TABLE_NAME,
                null,
                values,
                SQLiteDatabase.CONFLICT_IGNORE
            )
            if (insertedId > 0) {
                notifyMutation()
            }
            insertedId
        }

    override suspend fun update(record: SongRecord): Unit =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            val values = record.toContentValues(includeId = false)
            db.update(
                TABLE_NAME,
                values,
                "$COLUMN_ID = ? AND $COLUMN_STUDENT_ID = ?",
                arrayOf(record.id.toString(), record.studentId.toString())
            )
            notifyMutation()
        }

    override suspend fun setSaved(id: Long, studentId: Long, saved: Boolean): Unit =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            val values = ContentValues().apply {
                put(COLUMN_SAVED, if (saved) 1 else 0)
            }
            db.update(
                TABLE_NAME,
                values,
                "$COLUMN_ID = ? AND $COLUMN_STUDENT_ID = ?",
                arrayOf(id.toString(), studentId.toString())
            )
            notifyMutation()
        }

    override suspend fun setDuration(id: Long, durationMs: Long): Unit =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            val values = ContentValues().apply {
                put(COLUMN_DURATION_MS, durationMs)
            }
            db.update(
                TABLE_NAME,
                values,
                "$COLUMN_ID = ?",
                arrayOf(id.toString())
            )
            notifyMutation()
        }

    override suspend fun delete(record: SongRecord): Unit =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            db.delete(
                TABLE_NAME,
                "$COLUMN_ID = ? AND $COLUMN_STUDENT_ID = ?",
                arrayOf(record.id.toString(), record.studentId.toString())
            )
            notifyMutation()
        }

    override suspend fun clearUnsavedHistory(studentId: Long): Unit =
        withContext(Dispatchers.IO) {
            val db = dbHelper.writableDatabase
            db.delete(
                TABLE_NAME,
                "$COLUMN_STUDENT_ID = ? AND $COLUMN_SAVED = 0",
                arrayOf(studentId.toString())
            )
            notifyMutation()
        }

    companion object {
        const val TABLE_NAME = "songs"
        const val COLUMN_ID = "id"
        const val COLUMN_STUDENT_ID = "studentId"
        const val COLUMN_SUBJECT = "subject"
        const val COLUMN_UNIT = "unit"
        const val COLUMN_TOPIC_TITLE = "topicTitle"
        const val COLUMN_TOPIC_ID = "topicId"
        const val COLUMN_SONG_TITLE = "songTitle"
        const val COLUMN_REFERENCE_TITLE = "referenceTitle"
        const val COLUMN_LANGUAGE = "language"
        const val COLUMN_CATEGORY = "category"
        const val COLUMN_STYLE_NAME = "styleName"
        const val COLUMN_LYRICS = "lyrics"
        const val COLUMN_AUDIO_FILE_KEY = "audioFileKey"
        const val COLUMN_GENERATION_MODE = "generationMode"
        const val COLUMN_CREATED_AT = "createdAt"
        const val COLUMN_SAVED = "saved"
        const val COLUMN_DURATION_MS = "durationMs"
    }
}

private fun Cursor.toSongRecord(): SongRecord {
    return SongRecord(
        id = getLong(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_ID)),
        studentId = getLong(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_STUDENT_ID)),
        subject = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_SUBJECT)),
        unit = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_UNIT)),
        topicTitle = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_TOPIC_TITLE)),
        topicId = getInt(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_TOPIC_ID)),
        songTitle = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_SONG_TITLE)),
        referenceTitle = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_REFERENCE_TITLE)),
        language = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_LANGUAGE)),
        category = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_CATEGORY)),
        styleName = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_STYLE_NAME)),
        lyrics = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_LYRICS)),
        audioFileKey = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_AUDIO_FILE_KEY)),
        generationMode = getString(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_GENERATION_MODE)),
        createdAt = getLong(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_CREATED_AT)),
        saved = getInt(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_SAVED)) == 1,
        durationMs = getLong(getColumnIndexOrThrow(SQLiteSongDao.COLUMN_DURATION_MS))
    )
}

private fun Cursor.toSongRecordList(): List<SongRecord> {
    val list = ArrayList<SongRecord>(count)
    while (moveToNext()) {
        list.add(toSongRecord())
    }
    return list
}

private fun SongRecord.toContentValues(includeId: Boolean): ContentValues {
    return ContentValues().apply {
        if (includeId && id > 0) {
            put(SQLiteSongDao.COLUMN_ID, id)
        }
        put(SQLiteSongDao.COLUMN_STUDENT_ID, studentId)
        put(SQLiteSongDao.COLUMN_SUBJECT, subject)
        put(SQLiteSongDao.COLUMN_UNIT, unit)
        put(SQLiteSongDao.COLUMN_TOPIC_TITLE, topicTitle)
        put(SQLiteSongDao.COLUMN_TOPIC_ID, topicId)
        put(SQLiteSongDao.COLUMN_SONG_TITLE, songTitle)
        put(SQLiteSongDao.COLUMN_REFERENCE_TITLE, referenceTitle)
        put(SQLiteSongDao.COLUMN_LANGUAGE, language)
        put(SQLiteSongDao.COLUMN_CATEGORY, category)
        put(SQLiteSongDao.COLUMN_STYLE_NAME, styleName)
        put(SQLiteSongDao.COLUMN_LYRICS, lyrics)
        put(SQLiteSongDao.COLUMN_AUDIO_FILE_KEY, audioFileKey)
        put(SQLiteSongDao.COLUMN_GENERATION_MODE, generationMode)
        put(SQLiteSongDao.COLUMN_CREATED_AT, createdAt)
        put(SQLiteSongDao.COLUMN_SAVED, if (saved) 1 else 0)
        put(SQLiteSongDao.COLUMN_DURATION_MS, durationMs)
    }
}
