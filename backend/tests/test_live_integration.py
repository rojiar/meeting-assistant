"""
Live integration tests — require real keys in project .env.

Run:
  ./scripts/run-live-tests.sh
  # or
  PYTHONPATH=. pytest backend/tests/test_live_integration.py --run-live -v
"""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from backend.agents.analysis import analyze_transcript
from backend.agents.rag import ask_meeting
from backend.config import (
    GOOGLE_API_KEY,
    JIRA_API_TOKEN,
    JIRA_EMAIL,
    JIRA_PROJECT_KEY,
    JIRA_SITE_URL,
)
from backend.models.schemas import (
    JiraPreviewIssue,
    MeetingAnalysis,
    MeetingRecord,
    MeetingTask,
)
from backend.services.embeddings import EmbeddingService
from backend.services.jira import create_issues
from backend.services.meeting_store import MeetingStore
from backend.services.transcript import (
    chunk_transcript,
    format_transcript,
    parse_transcript,
)
from backend.services.vector_store import VectorStore

pytestmark = pytest.mark.live

LIVE_TRANSCRIPT = """[۱۰:۰۰] تست: این یک جلسه تست یکپارچه‌سازی است.
[۱۰:۰۱] QA: deadline دمو جمعه است و باید Jira KAN بررسی شود."""


@pytest.mark.asyncio
async def test_google_embedding_live(google_configured: None):
    embedder = EmbeddingService()
    vectors = await embedder.embed(["سلام — تست embedding فارسی"])
    assert len(vectors) == 1
    assert len(vectors[0]) > 100


@pytest.mark.asyncio
async def test_google_embed_query_live(google_configured: None):
    embedder = EmbeddingService()
    vec = await embedder.embed_query("deadline release چیست؟")
    assert len(vec) > 100


@pytest.mark.asyncio
async def test_gemini_analysis_agent_live(google_configured: None):
    analysis = await analyze_transcript(LIVE_TRANSCRIPT)
    assert analysis.title
    assert analysis.summary
    assert isinstance(analysis.key_points, list)
    assert isinstance(analysis.tasks, list)
    assert len(analysis.summary) > 20


@pytest.mark.asyncio
async def test_full_ingest_and_rag_live(google_configured: None, tmp_path: Path):
    """End-to-end RAG with real embeddings + Gemini (analysis stubbed to avoid loop issues)."""
    store = MeetingStore(tmp_path / "meetings.db", legacy_json_dir=None)
    vectors = VectorStore(tmp_path / "chroma")

    turns = parse_transcript(LIVE_TRANSCRIPT)
    formatted = format_transcript(turns)
    meeting_id = MeetingStore.new_id()
    chunks = chunk_transcript(turns)
    await vectors.index_meeting(meeting_id, chunks)

    record = MeetingRecord(
        id=meeting_id,
        title="تست یکپارچه",
        transcript=formatted,
        analysis=MeetingAnalysis(
            title="تست یکپارچه",
            summary="جلسه تست deadline دمو جمعه",
            key_points=["deadline دمو جمعه"],
            decisions=[],
            tasks=[],
        ),
        created_at=MeetingStore.now_iso(),
        source="live-test",
    )
    store.save(record)

    assert len(vectors.load(meeting_id)) >= 1

    answer = await ask_meeting(meeting_id, "deadline دمو چه روزی است؟", vectors)
    assert answer.answer
    assert len(answer.answer) > 5
    assert any(kw in answer.answer for kw in ("جمعه", "Friday", "دمو", "deadline"))


@pytest.mark.asyncio
async def test_jira_auth_live(jira_configured: None):
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{JIRA_SITE_URL.rstrip('/')}/rest/api/3/myself",
            headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "accountId" in data or "emailAddress" in data


@pytest.mark.asyncio
async def test_jira_project_access_live(jira_configured: None):
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{JIRA_SITE_URL.rstrip('/')}/rest/api/3/project/{JIRA_PROJECT_KEY}",
            headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        )
    assert response.status_code == 200, response.text
    assert response.json().get("key") == JIRA_PROJECT_KEY


@pytest.mark.asyncio
async def test_jira_create_issue_live(jira_configured: None):
    issue = JiraPreviewIssue(
        summary="[MVP-LIVE-TEST] دستیار جلسه — auto integration test",
        description="*Created by:* pytest live test\n*Safe to delete.*",
        priority="Low",
        task_index=0,
    )
    created = await create_issues([issue])
    assert len(created) == 1
    assert created[0]["key"]
    assert created[0]["key"].startswith(f"{JIRA_PROJECT_KEY}-")


@pytest.mark.asyncio
async def test_google_api_key_env_loaded(google_configured: None):
    assert GOOGLE_API_KEY.startswith("AIza") or len(GOOGLE_API_KEY) > 20
