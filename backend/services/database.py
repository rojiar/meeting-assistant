"""SQLite schema and connection helpers for meeting persistence."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 3

MEETINGS_DDL = """
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    transcript TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    title_en TEXT NOT NULL DEFAULT '',
    key_points_json TEXT NOT NULL DEFAULT '[]',
    decisions_json TEXT NOT NULL DEFAULT '[]',
    tasks_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'upload'
);
"""

FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS meetings_fts USING fts5(
    meeting_id UNINDEXED,
    title,
    summary,
    tokenize='unicode61'
);
"""

APP_META_DDL = """
CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SPEAKER_MAP_DDL = """
CREATE TABLE IF NOT EXISTS speaker_jira_map (
    speaker_name TEXT PRIMARY KEY,
    jira_account_id TEXT NOT NULL,
    jira_display_name TEXT NOT NULL DEFAULT ''
);
"""


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def migrate_schema(conn: sqlite3.Connection) -> None:
    cols = _column_names(conn, "meetings")
    if "meeting_type" not in cols:
        conn.execute(
            "ALTER TABLE meetings ADD COLUMN meeting_type TEXT NOT NULL DEFAULT 'general'"
        )
    if "tags_json" not in cols:
        conn.execute(
            "ALTER TABLE meetings ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'"
        )
    if "project_key" not in cols:
        conn.execute(
            "ALTER TABLE meetings ADD COLUMN project_key TEXT NOT NULL DEFAULT ''"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_meetings_type ON meetings(meeting_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_meetings_project ON meetings(project_key)"
    )
    conn.executescript(FTS_DDL + SPEAKER_MAP_DDL)


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(MEETINGS_DDL + APP_META_DDL)
        migrate_schema(conn)
        conn.execute(
            "INSERT OR IGNORE INTO app_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.commit()


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def dumps_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)
