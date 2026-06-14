"""Shared pytest fixtures."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Sequence

import pytest
from dotenv import load_dotenv

from backend.models.schemas import (
    ChunkCitation,
    MeetingAnalysis,
    MeetingRecord,
    MeetingTask,
    RagAnswer,
    TranscriptChunk,
)
from backend.services.embeddings import EmbeddingService
from backend.services.meeting_store import MeetingStore
from backend.services.vector_store import VectorStore

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

SAMPLE_TRANSCRIPT = """[۰۹:۰۰] علی: صبح بخیر. API لاگین deploy شد.
[۰۹:۰۱] سارا: تست auth تا فردا.
[۰۹:۰۳] رضا: project key را KAN بگذاریم.
[۰۹:۰۵] علی: deadline release پنجشنبه است."""

SAMPLE_ANALYSIS = MeetingAnalysis(
    title="استنداپ تست",
    title_en="Sprint standup",
    summary="جلسه هماهنگی sprint.",
    key_points=["API deploy شد", "Jira KAN"],
    decisions=["release بعد از QA"],
    tasks=[
        MeetingTask(
            title="تست auth",
            title_en="Complete auth unit tests",
            assignee="سارا",
            deadline="tomorrow",
            priority="high",
            context="تست auth تا فردا",
            context_en="Finish auth unit tests by tomorrow",
            detail=(
                "مسیر login و refresh token در regression پوشش داده شده اما چند سناریوی edge "
                "هنوز flaky است. باید تست‌های واحد auth تکمیل و پایدار شوند تا sign-off release ممکن باشد."
            ),
            detail_en=(
                "Login and refresh paths are partly covered in regression but edge cases remain flaky. "
                "Auth unit tests must be completed and stabilized before release sign-off."
            ),
            acceptance_criteria=[
                "تست‌های واحد login، logout و refresh بدون flaky pass شوند",
                "نتیجه regression auth در کانال QA اعلام شود",
            ],
            acceptance_criteria_en=[
                "Unit tests for login, logout, and refresh pass without flakiness",
                "Auth regression result posted in QA channel",
            ],
        ),
        MeetingTask(
            title="مستندات API",
            title_en="Update API documentation",
            assignee="رضا",
            deadline="Wednesday",
            priority="medium",
            context="project key KAN",
            context_en="Update API docs; use Jira project key KAN",
            detail="endpointهای auth و نمونه request/response در مستندات به‌روز نیستند.",
            acceptance_criteria=["مستندات auth با API فعلی هم‌خوان باشد"],
        ),
    ],
)


class FakeEmbeddingService(EmbeddingService):
    """Deterministic embeddings for tests — no API calls."""

    def __init__(self) -> None:
        super().__init__(api_key="test-key")

    @staticmethod
    def _vector(text: str, dims: int = 8) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(dims)]

    async def embed(
        self, texts: Sequence[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_one(
        self, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[float]:
        return self._vector(text)

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
def tmp_data_dirs(tmp_path: Path) -> dict[str, Path]:
    db = tmp_path / "meetings.db"
    legacy = tmp_path / "meetings_json"
    chroma = tmp_path / "chroma"
    synthetic = tmp_path / "synthetic"
    legacy.mkdir()
    chroma.mkdir()
    synthetic.mkdir()
    (synthetic / "demo-meeting.txt").write_text(SAMPLE_TRANSCRIPT, encoding="utf-8")
    return {"db": db, "legacy": legacy, "chroma": chroma, "synthetic": synthetic}


@pytest.fixture
def meeting_store(tmp_data_dirs: dict[str, Path]) -> MeetingStore:
    return MeetingStore(
        tmp_data_dirs["db"],
        legacy_json_dir=tmp_data_dirs["legacy"],
    )


@pytest.fixture
def vector_store(tmp_data_dirs: dict[str, Path]) -> VectorStore:
    return VectorStore(tmp_data_dirs["chroma"], embedder=FakeEmbeddingService())


@pytest.fixture
def sample_record(meeting_store: MeetingStore) -> MeetingRecord:
    record = MeetingRecord(
        id="test-meeting-01",
        title=SAMPLE_ANALYSIS.title,
        transcript=SAMPLE_TRANSCRIPT,
        analysis=SAMPLE_ANALYSIS,
        created_at="2026-05-26T00:00:00+00:00",
        source="test",
    )
    meeting_store.save(record)
    return record


@pytest.fixture
def sample_chunks() -> list[TranscriptChunk]:
    return [
        TranscriptChunk(
            chunk_id="c0",
            speaker="علی",
            text="deadline release پنجشنبه",
            turn_indices=[0],
        ),
        TranscriptChunk(
            chunk_id="c1", speaker="سارا", text="تست auth تا فردا", turn_indices=[1]
        ),
        TranscriptChunk(
            chunk_id="c2", speaker="رضا", text="project key KAN", turn_indices=[2]
        ),
    ]


SAMPLE_RAG_ANSWER = RagAnswer(
    answer="طبق گفته علی، deadline release برای پنجشنبه است.",
    sources=[
        ChunkCitation(
            chunk_id="c0",
            speaker="علی",
            excerpt="deadline release پنجشنبه",
            text="deadline release پنجشنبه",
        )
    ],
    used_meeting_context=True,
)


@pytest.fixture
def sample_rag_answer() -> RagAnswer:
    return SAMPLE_RAG_ANSWER


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: integration tests that call real Google/Jira APIs (requires .env keys)",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live integration tests against Google AI and Jira APIs",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-live", default=False):
        return
    skip_live = pytest.mark.skip(
        reason="Pass --run-live to execute real API integration tests"
    )
    for item in items:
        if "live" in item.keywords or "live_api" in item.nodeid:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def google_configured() -> None:
    if not os.getenv("GOOGLE_API_KEY", "").strip():
        pytest.skip("GOOGLE_API_KEY not set in .env")


@pytest.fixture(scope="session")
def jira_configured() -> None:
    if (
        not os.getenv("JIRA_EMAIL", "").strip()
        or not os.getenv("JIRA_API_TOKEN", "").strip()
    ):
        pytest.skip("JIRA_EMAIL / JIRA_API_TOKEN not set in .env")
