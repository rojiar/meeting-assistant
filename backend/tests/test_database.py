"""Unit tests for SQLite schema helpers."""

from pathlib import Path

from backend.services.database import connect, get_meta, init_db, set_meta


class TestDatabaseSchema:
    def test_init_creates_meetings_table(self, tmp_path: Path) -> None:
        db = tmp_path / "schema.db"
        init_db(db)
        with connect(db) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='meetings'"
            ).fetchone()
        assert row is not None

    def test_app_meta_roundtrip(self, tmp_path: Path) -> None:
        db = tmp_path / "meta.db"
        init_db(db)
        with connect(db) as conn:
            set_meta(conn, "legacy_json_migrated", "1")
            conn.commit()
        with connect(db) as conn:
            assert get_meta(conn, "legacy_json_migrated") == "1"
            assert get_meta(conn, "missing") is None
