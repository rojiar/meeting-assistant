from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.schemas import FacilitationReport, MeetingAnalysis, MeetingRecord
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_RAG_ANSWER, SAMPLE_TRANSCRIPT


@pytest.fixture
def client(meeting_store, vector_store, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("backend.main.meeting_store", meeting_store)
    monkeypatch.setattr("backend.main.vector_store", vector_store)
    return TestClient(app)


class TestSearchAndExport:
    def test_list_with_search_query(self, client: TestClient, sample_record):
        response = client.get("/api/meetings", params={"q": "استنداپ"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_export_markdown(self, client: TestClient, sample_record):
        response = client.get(f"/api/meetings/{sample_record.id}/export")
        assert response.status_code == 200
        assert "markdown" in response.headers.get("content-type", "")
        assert "## Summary" in response.text


class TestFutureFeaturesApi:
    def test_list_tasks_endpoint(self, client: TestClient, sample_record):
        r = client.get("/api/tasks")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_speakers_endpoint(self, client: TestClient, sample_record):
        r = client.get(f"/api/meetings/{sample_record.id}/speakers")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_patch_meeting(self, client: TestClient, sample_record):
        r = client.patch(
            f"/api/meetings/{sample_record.id}",
            json={"tags": ["x"], "project_key": "P1"},
        )
        assert r.status_code == 200
        assert r.json()["tags"] == ["x"]

    def test_delete_meeting(
        self, meeting_store, vector_store, monkeypatch: pytest.MonkeyPatch
    ):
        from backend.models.schemas import MeetingRecord
        from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT

        record = MeetingRecord(
            id="del-me",
            title="del",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-05-26T00:00:00+00:00",
        )
        meeting_store.save(record)
        monkeypatch.setattr("backend.main.meeting_store", meeting_store)
        monkeypatch.setattr("backend.main.vector_store", vector_store)
        c = TestClient(app)
        assert c.delete("/api/meetings/del-me").status_code == 200
        assert meeting_store.get("del-me") is None

    def test_assignee_map_crud(
        self, monkeypatch: pytest.MonkeyPatch, tmp_data_dirs: dict
    ):
        from backend.services.assignee_map import AssigneeMapStore

        store = AssigneeMapStore(tmp_data_dirs["db"])
        monkeypatch.setattr("backend.main.assignee_map", store)
        c = TestClient(app)
        put = c.put(
            "/api/settings/assignee-map",
            json={
                "speaker_name": "علی",
                "jira_account_id": "a1",
                "jira_display_name": "",
            },
        )
        assert put.status_code == 200
        assert len(c.get("/api/settings/assignee-map").json()) == 1


class TestHealthEndpoint:
    def test_health_ok(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "google_api" in data
        assert "jira_site" in data
        assert "database" in data
        assert data["database"].endswith("meetings.db")
        assert "logfire" in data
        assert isinstance(data["logfire"], bool)


class TestMeetingsList:
    def test_list_empty(self, client: TestClient):
        assert client.get("/api/meetings").json() == []

    def test_list_with_record(self, client: TestClient, sample_record):
        data = client.get("/api/meetings").json()
        assert len(data) == 1
        assert data[0]["id"] == sample_record.id


class TestGetMeeting:
    def test_get_existing(self, client: TestClient, sample_record):
        response = client.get(f"/api/meetings/{sample_record.id}")
        assert response.status_code == 200
        assert response.json()["title"] == sample_record.title

    def test_get_not_found(self, client: TestClient):
        response = client.get("/api/meetings/does-not-exist")
        assert response.status_code == 404
        assert "Meeting not found" in response.json()["detail"]


class TestCreateMeeting:
    def test_empty_transcript_400(self, client: TestClient):
        response = client.post("/api/meetings", json={"transcript": "  "})
        assert response.status_code == 400

    def test_create_success(self, client: TestClient):
        mock_record = MeetingRecord(
            id="new1",
            title="t",
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            created_at="2026-01-01T00:00:00+00:00",
        )
        with patch(
            "backend.main.ingest_meeting", new=AsyncMock(return_value=mock_record)
        ):
            response = client.post(
                "/api/meetings",
                json={"transcript": SAMPLE_TRANSCRIPT, "title": "t"},
            )
        assert response.status_code == 200
        assert response.json()["id"] == "new1"

    def test_create_value_error_400(self, client: TestClient):
        with patch(
            "backend.main.ingest_meeting",
            new=AsyncMock(side_effect=ValueError("bad transcript")),
        ):
            response = client.post("/api/meetings", json={"transcript": "x"})
        assert response.status_code == 400

    def test_create_gemini_dunning_403(self, client: TestClient):
        from pydantic_ai.exceptions import ModelHTTPError

        dunning = ModelHTTPError(
            status_code=403,
            model_name="gemini-2.5-flash",
            body={
                "error": {
                    "code": 403,
                    "message": "Lightning dunning decision is deny for project: projects/390415010751",
                    "status": "PERMISSION_DENIED",
                }
            },
        )
        with patch(
            "backend.main.ingest_meeting",
            new=AsyncMock(side_effect=dunning),
        ):
            response = client.post("/api/meetings", json={"transcript": "x"})
        assert response.status_code == 403
        assert "billing" in response.json()["detail"]
        assert "status_code:" not in response.json()["detail"]

    def test_ask_gemini_dunning_403(self, client: TestClient, sample_record):
        from pydantic_ai.exceptions import ModelHTTPError

        dunning = ModelHTTPError(
            status_code=403,
            model_name="gemini-2.5-flash",
            body={
                "error": {
                    "message": "Lightning dunning decision is deny for project: projects/390415010751",
                }
            },
        )
        with patch(
            "backend.main.ask_meeting",
            new=AsyncMock(side_effect=dunning),
        ):
            response = client.post(
                f"/api/meetings/{sample_record.id}/ask",
                json={"question": "deadline?"},
            )
        assert response.status_code == 403
        assert "billing" in response.json()["detail"]


class TestFacilitationEndpoint:
    def test_facilitation_not_found(self, client: TestClient):
        response = client.get("/api/meetings/nope/facilitation")
        assert response.status_code == 404

    def test_facilitation_returns_coaching_fields(
        self, client: TestClient, sample_record
    ):
        report = FacilitationReport(
            what_went_well=["نکته مثبت"],
            improvements=["پیشنهاد"],
            next_meeting_agenda=["دستور کار"],
            timebox_suggestion="۳۰ دقیقه",
            coaching_summary="جمع‌بندی",
            facilitator_score=3,
        )
        with patch(
            "backend.main.build_facilitation_report",
            new=AsyncMock(return_value=report),
        ):
            response = client.get(f"/api/meetings/{sample_record.id}/facilitation")
        assert response.status_code == 200
        body = response.json()
        assert body["what_went_well"] == ["نکته مثبت"]
        assert body["facilitator_score"] == 3


class TestSyntheticEndpoint:
    def test_synthetic_not_found(self, client: TestClient):
        response = client.post("/api/meetings/synthetic/missing-file")
        assert response.status_code == 404


class TestAskEndpoint:
    def test_ask_meeting_not_found(self, client: TestClient):
        response = client.post("/api/meetings/nope/ask", json={"question": "سوال"})
        assert response.status_code == 404

    def test_ask_empty_question_400(self, client: TestClient, sample_record):
        response = client.post(
            f"/api/meetings/{sample_record.id}/ask",
            json={"question": "   "},
        )
        assert response.status_code == 400

    def test_ask_success(self, client: TestClient, sample_record):
        with patch(
            "backend.main.ask_meeting", new=AsyncMock(return_value=SAMPLE_RAG_ANSWER)
        ):
            response = client.post(
                f"/api/meetings/{sample_record.id}/ask",
                json={"question": "deadline?"},
            )
        assert response.status_code == 200
        assert "پنجشنبه" in response.json()["answer"]
        assert response.json()["sources"][0]["chunk_id"] == "c0"


class TestJiraEndpoints:
    def test_preview_not_found(self, client: TestClient):
        assert client.post("/api/meetings/x/jira/preview").status_code == 404

    def test_preview_success(self, client: TestClient, sample_record):
        response = client.post(f"/api/meetings/{sample_record.id}/jira/preview")
        assert response.status_code == 200
        issues = response.json()["issues"]
        assert len(issues) == 2
        assert issues[0]["priority"] == "High"

    def test_create_no_tasks_400(self, meeting_store, vector_store, monkeypatch):
        empty = MeetingRecord(
            id="empty-tasks",
            title="t",
            transcript="t",
            analysis=MeetingAnalysis(title="t", summary="s", tasks=[]),
            created_at="2026-01-01T00:00:00+00:00",
        )
        meeting_store.save(empty)
        monkeypatch.setattr("backend.main.meeting_store", meeting_store)
        monkeypatch.setattr("backend.main.vector_store", vector_store)
        client = TestClient(app)
        response = client.post("/api/meetings/empty-tasks/jira/create")
        assert response.status_code == 400

    def test_create_success(self, client: TestClient, sample_record):
        with patch(
            "backend.main.create_issues",
            new=AsyncMock(return_value=[{"key": "KAN-1", "summary": "تست auth"}]),
        ):
            response = client.post(f"/api/meetings/{sample_record.id}/jira/create")
        assert response.status_code == 200
        assert response.json()["created"][0]["key"] == "KAN-1"

    def test_create_selected_indices_only(self, client: TestClient, sample_record):
        with patch(
            "backend.main.create_issues", new=AsyncMock(return_value=[])
        ) as mock_create:
            client.post(
                f"/api/meetings/{sample_record.id}/jira/create",
                json={"task_indices": [1]},
            )
        selected = mock_create.call_args[0][0]
        assert len(selected) == 1
        assert selected[0].task_index == 1

    def test_create_invalid_index_returns_400(self, client: TestClient, sample_record):
        response = client.post(
            f"/api/meetings/{sample_record.id}/jira/create",
            json={"task_indices": [99]},
        )
        assert response.status_code == 400
