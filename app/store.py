import os
import sqlite3
from pathlib import Path

RUNTIME = Path(os.getenv('APP_DATA_DIR', Path(__file__).resolve().parents[1] / 'runtime'))


def connect():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(RUNTIME / 'app.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def init():
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, sap TEXT, role TEXT, expires REAL);
        CREATE TABLE IF NOT EXISTS songs(id TEXT PRIMARY KEY, sap TEXT, topic TEXT, language TEXT CHECK(language IN ('en','hi')),
            title TEXT, lyrics TEXT, settings TEXT, provenance TEXT, status TEXT, audio TEXT, mime TEXT, error TEXT,
            provider_lyrics TEXT, source_hash TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, sap TEXT, topic TEXT, score INTEGER, total INTEGER, created REAL);
        CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY, topic TEXT, name TEXT, excerpt TEXT, filename TEXT,
            approved INTEGER DEFAULT 0, created REAL);
        ''')
        columns = {row[1] for row in db.execute('PRAGMA table_info(songs)')}
        if 'audio_origin' not in columns:
            db.execute('ALTER TABLE songs ADD COLUMN audio_origin TEXT')
        db.execute("UPDATE songs SET status='failed', error='Server restarted before generation finished. Retry synthesis.' WHERE status='generating'")


def rows(query, args=()):
    with connect() as db:
        return [dict(row) for row in db.execute(query, args)]


def execute(query, args=()):
    with connect() as db:
        db.execute(query, args)
