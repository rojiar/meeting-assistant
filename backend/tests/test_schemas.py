import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    AskRequest,
    CreateMeetingRequest,
    FacilitationReport,
    JiraCreateRequest,
    MeetingAnalysis,
    MeetingRecord,
    MeetingTask,
    RagAnswer,
)


class TestMeetingTask:
    def test_valid_task(self):
        task = MeetingTask(title="کار", priority="high", context="ctx")
        assert task.priority == "high"

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            MeetingTask(title="x", priority="urgent", context="c")

    def test_optional_fields_default_none(self):
        task = MeetingTask(title="t", context="c")
        assert task.assignee is None
        assert task.deadline is None
        assert task.priority == "medium"


class TestMeetingAnalysis:
    def test_defaults_empty_lists(self):
        analysis = MeetingAnalysis(title="t", summary="s")
        assert analysis.key_points == []
        assert analysis.decisions == []
        assert analysis.tasks == []


class TestMeetingRecord:
    def test_serialization_roundtrip(self, sample_record: MeetingRecord):
        json_str = sample_record.model_dump_json()
        restored = MeetingRecord.model_validate_json(json_str)
        assert restored.id == sample_record.id
        assert restored.analysis.tasks[0].title == "تست auth"


class TestRagAnswer:
    def test_empty_sources_allowed(self):
        answer = RagAnswer(answer="پاسخ")
        assert answer.sources == []


class TestRequestModels:
    def test_create_meeting_request(self):
        req = CreateMeetingRequest(transcript="[۰۹:۰۰] a: b")
        assert req.title is None

    def test_ask_request(self):
        req = AskRequest(question="سوال؟")
        assert req.question == "سوال؟"

    def test_jira_create_optional_indices(self):
        req = JiraCreateRequest()
        assert req.task_indices is None

    def test_jira_create_with_indices(self):
        req = JiraCreateRequest(task_indices=[0, 2])
        assert req.task_indices == [0, 2]


class TestFacilitationReport:
    def test_valid_report(self):
        report = FacilitationReport(
            what_went_well=["خوب"],
            improvements=["بهتر"],
            next_meeting_agenda=["بند ۱"],
            timebox_suggestion="۴۵ دقیقه",
            coaching_summary="خلاصه",
            facilitator_score=5,
        )
        assert report.facilitator_score == 5

    def test_facilitator_score_bounds(self):
        with pytest.raises(ValidationError):
            FacilitationReport(facilitator_score=0)
        with pytest.raises(ValidationError):
            FacilitationReport(facilitator_score=6)

    def test_optional_score_defaults_none(self):
        report = FacilitationReport()
        assert report.facilitator_score is None
        assert report.what_went_well == []
