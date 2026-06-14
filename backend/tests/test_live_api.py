"""
Live HTTP API tests — real FastAPI routes + real Google/Jira credentials.

Uses one end-to-end test per Gemini session to avoid event-loop issues with Pydantic AI.
Run: ./scripts/run-live-tests.sh
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from backend import main
from backend.main import app
from backend.models.schemas import MeetingAnalysis, MeetingRecord
from backend.services.meeting_store import MeetingStore
from backend.services.vector_store import VectorStore
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT
from backend.tests.test_live_integration import LIVE_TRANSCRIPT

pytestmark = pytest.mark.live


@pytest.fixture
async def live_api_client(
    tmp_path: Path,
    google_configured: None,
    monkeypatch: pytest.MonkeyPatch,
):
    db = tmp_path / "live-api.db"
    chroma = tmp_path / "live-api-chroma"
    store = MeetingStore(db, legacy_json_dir=None)
    vectors = VectorStore(chroma)
    monkeypatch.setattr("backend.main.meeting_store", store)
    monkeypatch.setattr("backend.main.vector_store", vectors)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=120.0,
    ) as client:
        yield client, store


@pytest.mark.asyncio
async def test_live_api_health(live_api_client):
    client, _store = live_api_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["google_api"] is True
    assert "database" in data


@pytest.mark.asyncio
async def test_live_api_end_to_end_gemini_and_rag(live_api_client):
    """Single flow: create → get → list → RAG → chitchat (one Gemini analysis call)."""
    client, store = live_api_client

    created = await client.post(
        "/api/meetings",
        json={"transcript": LIVE_TRANSCRIPT, "title": "Live API E2E"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    meeting_id = body["id"]
    assert body["analysis"]["summary"]
    assert len(body["analysis"]["summary"]) > 10

    fetched = await client.get(f"/api/meetings/{meeting_id}")
    assert fetched.status_code == 200
    assert fetched.json()["analysis"]["summary"] == body["analysis"]["summary"]
    assert store.get(meeting_id) is not None

    listed = await client.get("/api/meetings")
    assert listed.status_code == 200
    assert any(m["id"] == meeting_id for m in listed.json())

    rag = await client.post(
        f"/api/meetings/{meeting_id}/ask",
        json={"question": "deadline دمو چه روزی است؟"},
    )
    assert rag.status_code == 200, rag.text
    assert len(rag.json()["answer"]) > 5

    hello = await client.post(
        f"/api/meetings/{meeting_id}/ask",
        json={"question": "hello"},
    )
    assert hello.status_code == 200
    hello_body = hello.json()
    assert hello_body.get("used_meeting_context") is False
    assert hello_body["sources"] == []


@pytest.mark.asyncio
async def test_live_api_jira_preview_http(jira_configured: None, live_api_client):
    """Jira preview route with tasks persisted in SQLite (analysis mocked)."""
    client, store = live_api_client
    record = MeetingRecord(
        id="jira-preview-live",
        title="تست",
        transcript=SAMPLE_TRANSCRIPT,
        analysis=SAMPLE_ANALYSIS,
        created_at=MeetingStore.now_iso(),
        source="live-test",
    )
    store.save(record)

    preview = await client.post(f"/api/meetings/{record.id}/jira/preview")
    assert preview.status_code == 200, preview.text
    issues = preview.json()["issues"]
    assert len(issues) >= 1
    assert issues[0]["summary"]


@pytest.mark.asyncio
async def test_live_api_create_with_mocked_analysis(live_api_client):
    """HTTP ingest + SQLite without extra Gemini call (vector index only)."""
    client, store = live_api_client
    with patch(
        "backend.services.ingest.analyze_transcript",
        new=AsyncMock(return_value=SAMPLE_ANALYSIS),
    ):
        response = await client.post(
            "/api/meetings",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )
    assert response.status_code == 200, response.text
    meeting_id = response.json()["id"]
    assert store.get(meeting_id) is not None
    assert store.get(meeting_id).analysis.summary == SAMPLE_ANALYSIS.summary


@pytest.mark.asyncio
async def test_live_api_facilitation(live_api_client):
    """Real Gemini call for facilitation guide on a persisted meeting."""
    client, store = live_api_client
    record = MeetingRecord(
        id="facilitation-live",
        title="Live facilitation",
        transcript=SAMPLE_TRANSCRIPT,
        analysis=SAMPLE_ANALYSIS,
        created_at=MeetingStore.now_iso(),
        source="live-test",
        meeting_type="standup",
    )
    store.save(record)

    response = await client.get(f"/api/meetings/{record.id}/facilitation")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data["what_went_well"], list)
    assert isinstance(data["improvements"], list)
    assert len(data["coaching_summary"]) > 10
    assert data["facilitator_score"] is None or 1 <= data["facilitator_score"] <= 5
