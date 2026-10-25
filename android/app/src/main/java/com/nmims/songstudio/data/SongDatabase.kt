package com.nmims.songstudio.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * SQLiteOpenHelper-based persistence layer for the song library.
 * Requires no Room or KSP dependencies, relying strictly on standard Android SDK SQLite APIs.
 */
open class SongDatabase(
    context: Context,
    name: String = DATABASE_NAME
) : SQLiteOpenHelper(context.applicationContext, name, null, DATABASE_VERSION) {

    private val dao: SongDao = SQLiteSongDao(this)

    open fun songDao(): SongDao = dao

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE IF NOT EXISTS ${SQLiteSongDao.TABLE_NAME} (
                ${SQLiteSongDao.COLUMN_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                ${SQLiteSongDao.COLUMN_STUDENT_ID} INTEGER NOT NULL,
                ${SQLiteSongDao.COLUMN_SUBJECT} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_UNIT} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_TOPIC_TITLE} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_TOPIC_ID} INTEGER NOT NULL,
                ${SQLiteSongDao.COLUMN_SONG_TITLE} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_REFERENCE_TITLE} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_LANGUAGE} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_CATEGORY} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_STYLE_NAME} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_LYRICS} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_AUDIO_FILE_KEY} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_GENERATION_MODE} TEXT NOT NULL,
                ${SQLiteSongDao.COLUMN_CREATED_AT} INTEGER NOT NULL,
                ${SQLiteSongDao.COLUMN_SAVED} INTEGER NOT NULL DEFAULT 0,
                ${SQLiteSongDao.COLUMN_DURATION_MS} INTEGER NOT NULL DEFAULT 0
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS index_songs_studentId_audioFileKey
            ON ${SQLiteSongDao.TABLE_NAME} (
                ${SQLiteSongDao.COLUMN_STUDENT_ID},
                ${SQLiteSongDao.COLUMN_AUDIO_FILE_KEY}
            )
            """.trimIndent()
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Safe migration hook for future schema updates
    }

    companion object {
        const val DATABASE_NAME = "song_library.db"
        const val DATABASE_VERSION = 1

        @Volatile
        private var instance: SongDatabase? = null

        fun get(context: Context, name: String = DATABASE_NAME): SongDatabase =
            instance ?: synchronized(this) {
                instance ?: SongDatabase(context.applicationContext, name).also { instance = it }
            }

        /** Visible for testing: create a fresh named or isolated instance. */
        fun create(context: Context, name: String): SongDatabase =
            SongDatabase(context.applicationContext, name)
    }
}
