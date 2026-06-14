from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.agents.facilitation import suggest_facilitation
from backend.main import app
from backend.models.schemas import FacilitationReport, MeetingAnalysis, MeetingRecord
from backend.services.facilitation import build_facilitation_report
from backend.services.stats import speaker_participation
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


SAMPLE_FACILITATION = FacilitationReport(
    what_went_well=["تصمیمات شفاف ثبت شد", "مشارکت متعادل بود"],
    improvements=["بخش فنی timebox شود", "UX قبل از تصمیم فنی بحث شود"],
    next_meeting_agenda=["بررسی blockerها", "تأیید QA sign-off"],
    timebox_suggestion="جلسه بعد ۴۵ دقیقه: ۱۰ دقیقه context، ۲۰ فنی، ۱۰ تصمیم، ۵ جمع‌بندی.",
    coaching_summary="جلسه مؤثر بود؛ با timebox واضح‌تر می‌تواند کوتاه‌تر شود.",
    facilitator_score=4,
)


class TestSuggestFacilitationAgent:
    @pytest.mark.asyncio
    async def test_builds_prompt_with_stats_and_analysis(self):
        stats = speaker_participation(SAMPLE_TRANSCRIPT)
        mock_result = MagicMock()
        mock_result.output = SAMPLE_FACILITATION

        with patch(
            "backend.agents.facilitation.facilitation_agent.run",
            new=AsyncMock(return_value=mock_result),
        ) as mock_run:
            report = await suggest_facilitation(
                transcript=SAMPLE_TRANSCRIPT,
                analysis=SAMPLE_ANALYSIS,
                meeting_type="standup",
                speaker_stats=stats,
            )

        assert report == SAMPLE_FACILITATION
        mock_run.assert_awaited_once()
        prompt = mock_run.call_args.args[0]
        assert "standup" in prompt
        assert SAMPLE_ANALYSIS.summary in prompt
        assert "تست auth" in prompt
        assert stats[0]["speaker"] in prompt
        assert "Transcript" in prompt

    @pytest.mark.asyncio
    async def test_empty_stats_renders_dash(self):
        mock_result = MagicMock()
        mock_result.output = FacilitationReport(coaching_summary="ok")

        with patch(
            "backend.agents.facilitation.facilitation_agent.run",
            new=AsyncMock(return_value=mock_result),
        ) as mock_run:
            await suggest_facilitation(
                transcript="[۰۹:۰۰] a: b",
                analysis=MeetingAnalysis(title="t", summary="s"),
                meeting_type="general",
                speaker_stats=[],
            )

        prompt = mock_run.call_args.args[0]
        assert "آمار مشارکت گویندگان:" in prompt
        assert "—" in prompt


class TestBuildFacilitationReport:
    @pytest.mark.asyncio
    async def test_delegates_to_agent(self, sample_record: MeetingRecord):
        with patch(
            "backend.services.facilitation.suggest_facilitation",
            new=AsyncMock(return_value=SAMPLE_FACILITATION),
        ) as mock_suggest:
            report = await build_facilitation_report(sample_record)

        assert report.facilitator_score == 4
        assert len(report.improvements) == 2
        mock_suggest.assert_awaited_once()
        kwargs = mock_suggest.call_args.kwargs
        assert kwargs["transcript"] == sample_record.transcript
        assert kwargs["analysis"] == sample_record.analysis
        assert kwargs["meeting_type"] == sample_record.meeting_type
        assert isinstance(kwargs["speaker_stats"], list)

    @pytest.mark.asyncio
    async def test_passes_computed_speaker_stats(self, sample_record: MeetingRecord):
        expected = speaker_participation(sample_record.transcript)

        with patch(
            "backend.services.facilitation.suggest_facilitation",
            new=AsyncMock(return_value=SAMPLE_FACILITATION),
        ) as mock_suggest:
            await build_facilitation_report(sample_record)

        stats = mock_suggest.call_args.kwargs["speaker_stats"]
        assert stats == expected
        assert sum(s["percent"] for s in stats) == pytest.approx(100.0)


class TestFacilitationApi:
    @pytest.fixture
    def client(self, meeting_store, vector_store, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("backend.main.meeting_store", meeting_store)
        monkeypatch.setattr("backend.main.vector_store", vector_store)
        return TestClient(app)

    def test_facilitation_not_found(self, client: TestClient):
        response = client.get("/api/meetings/missing/facilitation")
        assert response.status_code == 404
        assert "Meeting not found" in response.json()["detail"]

    def test_facilitation_success_full_shape(self, client: TestClient, sample_record):
        with patch(
            "backend.main.build_facilitation_report",
            new=AsyncMock(return_value=SAMPLE_FACILITATION),
        ):
            response = client.get(f"/api/meetings/{sample_record.id}/facilitation")
        assert response.status_code == 200
        data = response.json()
        assert data["facilitator_score"] == 4
        assert len(data["what_went_well"]) == 2
        assert len(data["improvements"]) == 2
        assert len(data["next_meeting_agenda"]) == 2
        assert data["coaching_summary"]
        assert "دقیقه" in data["timebox_suggestion"]

    def test_facilitation_gemini_dunning_403(self, client: TestClient, sample_record):
        from pydantic_ai.exceptions import ModelHTTPError

        err = ModelHTTPError(
            status_code=403,
            model_name="gemini-3.5-flash",
            body={"error": {"message": "Lightning dunning decision is deny"}},
        )
        with patch(
            "backend.main.build_facilitation_report",
            new=AsyncMock(side_effect=err),
        ):
            response = client.get(f"/api/meetings/{sample_record.id}/facilitation")
        assert response.status_code == 403
        assert "billing" in response.json()["detail"]

    def test_facilitation_generic_error_502(self, client: TestClient, sample_record):
        with patch(
            "backend.main.build_facilitation_report",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            response = client.get(f"/api/meetings/{sample_record.id}/facilitation")
        assert response.status_code == 502
        assert "facilitation guide" in response.json()["detail"]
