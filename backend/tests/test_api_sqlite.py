"""API + SQLite integration (unit, no external APIs)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


@pytest.fixture
def sqlite_client(meeting_store, vector_store, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("backend.main.meeting_store", meeting_store)
    monkeypatch.setattr("backend.main.vector_store", vector_store)
    return TestClient(app)


class TestApiSqliteIntegration:
    def test_health_reports_database_path(self, sqlite_client: TestClient):
        data = sqlite_client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "database" in data
        assert data["database"].endswith("meetings.db")

    def test_create_then_get_persists_summary(
        self, sqlite_client: TestClient, meeting_store
    ):
        with patch(
            "backend.services.ingest.analyze_transcript",
            new=AsyncMock(return_value=SAMPLE_ANALYSIS),
        ):
            created = sqlite_client.post(
                "/api/meetings",
                json={"transcript": SAMPLE_TRANSCRIPT},
            )
        assert created.status_code == 200
        meeting_id = created.json()["id"]

        loaded = sqlite_client.get(f"/api/meetings/{meeting_id}").json()
        assert loaded["analysis"]["summary"] == SAMPLE_ANALYSIS.summary
        assert loaded["analysis"]["key_points"] == SAMPLE_ANALYSIS.key_points

        stored = meeting_store.get(meeting_id)
        assert stored is not None
        assert stored.analysis.summary == SAMPLE_ANALYSIS.summary
