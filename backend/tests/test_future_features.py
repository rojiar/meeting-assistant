"""Tests for Sprint 2/3 lite features."""

from backend.models.schemas import MeetingRecord, SpeakerJiraMap, UpdateMeetingRequest
from backend.services.assignee_map import AssigneeMapStore
from backend.services.stats import speaker_participation
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


class TestTagsAndFilters:
    def test_create_with_tags_and_project(self, meeting_store):
        record = MeetingRecord(
            id="tag1",
            title="Tagged",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-05-26T00:00:00+00:00",
            tags=["sprint-1", "backend"],
            project_key="KAN",
            meeting_type="standup",
        )
        meeting_store.save(record)
        hits = meeting_store.list_all(tag="sprint-1")
        assert len(hits) == 1
        assert meeting_store.list_all(project_key="KAN")[0].id == "tag1"
        assert meeting_store.list_all(meeting_type="standup")[0].id == "tag1"

    def test_update_metadata(self, meeting_store, sample_record):
        updated = meeting_store.update(
            sample_record.id,
            UpdateMeetingRequest(tags=["demo"], project_key="PROJ"),
        )
        assert updated is not None
        assert updated.tags == ["demo"]
        assert updated.project_key == "PROJ"


class TestDeleteMeeting:
    def test_delete_removes_record(self, meeting_store, sample_record):
        assert meeting_store.delete(sample_record.id) is True
        assert meeting_store.get(sample_record.id) is None


class TestActionItems:
    def test_list_all_tasks(self, meeting_store, sample_record):
        items = meeting_store.list_action_items()
        assert len(items) >= 2
        assert items[0].meeting_id == sample_record.id

    def test_open_only_excludes_jira(self, meeting_store):
        record = MeetingRecord(
            id="jira-task",
            title="t",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS.model_copy(
                update={
                    "tasks": [
                        SAMPLE_ANALYSIS.tasks[0].model_copy(
                            update={"jira_key": "KAN-99"}
                        )
                    ]
                }
            ),
            created_at="2026-05-26T00:00:00+00:00",
        )
        meeting_store.save(record)
        open_items = meeting_store.list_action_items(open_only=True)
        assert all(i.jira_key is None for i in open_items)


class TestSpeakerStats:
    def test_participation_percentages(self):
        stats = speaker_participation(SAMPLE_TRANSCRIPT)
        assert len(stats) >= 2
        assert sum(s["percent"] for s in stats) == 100.0


class TestAssigneeMap:
    def test_upsert_and_resolve(self, tmp_data_dirs):
        store = AssigneeMapStore(tmp_data_dirs["db"])
        store.upsert(
            SpeakerJiraMap(
                speaker_name="سارا",
                jira_account_id="acc-123",
                jira_display_name="Sara",
            )
        )
        assert store.resolve_account_id("سارا") == "acc-123"
        assert store.resolve_account_id("unknown") is None
        assert len(store.list_all()) == 1
