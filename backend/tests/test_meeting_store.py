import json
from pathlib import Path

import pytest

from backend.models.schemas import MeetingRecord
from backend.services.database import connect
from backend.services.meeting_store import MeetingStore
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


class TestMeetingStoreCRUD:
    def test_save_and_get(self, meeting_store: MeetingStore):
        record = MeetingRecord(
            id="abc123",
            title="t",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-01-01T00:00:00+00:00",
        )
        meeting_store.save(record)
        loaded = meeting_store.get("abc123")
        assert loaded is not None
        assert loaded.title == "t"

    def test_get_missing_returns_none(self, meeting_store: MeetingStore):
        assert meeting_store.get("missing") is None

    def test_list_all_sorted_newest_first(self, meeting_store: MeetingStore):
        r1 = MeetingRecord(
            id="1",
            title="old",
            transcript="t",
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-01-01T00:00:00+00:00",
        )
        r2 = MeetingRecord(
            id="2",
            title="new",
            transcript="t",
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-02-01T00:00:00+00:00",
        )
        meeting_store.save(r1)
        meeting_store.save(r2)
        titles = [r.title for r in meeting_store.list_all()]
        assert titles == ["new", "old"]


class TestSyntheticFiles:
    def test_list_synthetic(
        self, tmp_data_dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "backend.services.meeting_store.SYNTHETIC_DIR",
            tmp_data_dirs["synthetic"],
        )
        store = MeetingStore(
            tmp_data_dirs["db"],
            legacy_json_dir=tmp_data_dirs["legacy"],
        )
        items = store.list_synthetic()
        assert len(items) == 1
        assert items[0]["id"] == "demo-meeting"

    def test_load_synthetic(
        self, tmp_data_dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "backend.services.meeting_store.SYNTHETIC_DIR",
            tmp_data_dirs["synthetic"],
        )
        store = MeetingStore(
            tmp_data_dirs["db"],
            legacy_json_dir=tmp_data_dirs["legacy"],
        )
        text = store.load_synthetic("demo-meeting")
        assert "علی" in text

    def test_load_synthetic_not_found(
        self, tmp_data_dirs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "backend.services.meeting_store.SYNTHETIC_DIR",
            tmp_data_dirs["synthetic"],
        )
        store = MeetingStore(
            tmp_data_dirs["db"],
            legacy_json_dir=tmp_data_dirs["legacy"],
        )
        with pytest.raises(FileNotFoundError):
            store.load_synthetic("no-such-file")


class TestLegacyJsonMigration:
    def test_migrates_json_files_once(self, tmp_data_dirs: dict[str, Path]) -> None:
        legacy = tmp_data_dirs["legacy"]
        record = MeetingRecord(
            id="legacy01",
            title="قدیمی",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-01-01T00:00:00+00:00",
        )
        (legacy / "legacy01.json").write_text(
            record.model_dump_json(), encoding="utf-8"
        )

        store = MeetingStore(
            tmp_data_dirs["db"],
            legacy_json_dir=legacy,
        )
        loaded = store.get("legacy01")
        assert loaded is not None
        assert loaded.analysis.summary == SAMPLE_ANALYSIS.summary

        store2 = MeetingStore(
            tmp_data_dirs["db"],
            legacy_json_dir=legacy,
        )
        assert len(store2.list_all()) == 1

    def test_summary_stored_in_sqlite(self, meeting_store: MeetingStore) -> None:
        record = MeetingRecord(
            id="sum1",
            title="t",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-01-01T00:00:00+00:00",
        )
        meeting_store.save(record)
        with connect(meeting_store.db_path) as conn:
            row = conn.execute(
                "SELECT summary, key_points_json FROM meetings WHERE id = ?",
                ("sum1",),
            ).fetchone()
        assert row["summary"] == SAMPLE_ANALYSIS.summary
        assert "API deploy" in json.loads(row["key_points_json"])[0]


class TestMeetingStoreHelpers:
    def test_new_id_length(self):
        assert len(MeetingStore.new_id()) == 12

    def test_now_iso_contains_t(self):
        assert "T" in MeetingStore.now_iso()
