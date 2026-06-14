import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.schemas import MeetingTask
from backend.services.jira import (
    PRIORITY_MAP,
    _auth_header,
    build_issue_description,
    build_issue_payload,
    create_issues,
    preview_issues,
)


class TestBuildIssueDescription:
    def test_includes_rich_english_sections(self):
        task = MeetingTask(
            title="Fix bug",
            title_en="Fix refresh token bug",
            assignee="Ali",
            deadline="today at 2pm",
            priority="high",
            context="race condition in refresh token",
            detail=(
                "When a user has two tabs open, one refresh request returns 401. "
                "Likely a race in session storage; fix before smoke test."
            ),
            acceptance_criteria=[
                "Two tabs refresh without 401",
                "Login/refresh smoke test passes after fix",
            ],
        )
        desc = build_issue_description(task, "Sprint standup")
        assert "*Work description:*" in desc
        assert "race condition" in desc
        assert "*Acceptance criteria:*" in desc
        assert "Two tabs refresh" in desc
        assert "*Meeting:* Sprint standup" in desc
        assert "*Context:* race condition in refresh token" in desc
        assert "*Suggested assignee:* Ali" in desc
        assert "*Deadline:* today at 2pm" in desc
        assert "*Priority:* High" in desc

    def test_falls_back_to_context_when_detail_missing(self):
        task = MeetingTask(title="Fix bug", context="token issue")
        desc = build_issue_description(task, "Meeting")
        assert "*Work description:*\ntoken issue" in desc
        assert "*Context:*" not in desc

    def test_uses_english_criteria_when_primary_missing(self):
        task = MeetingTask(
            title="T",
            context="ctx",
            acceptance_criteria_en=["Done when tests pass"],
        )
        desc = build_issue_description(task, "Meeting")
        assert "- Done when tests pass" in desc


class TestBuildIssuePayload:
    def test_uses_english_summary_and_description(self):
        task = MeetingTask(
            title="Fix bug",
            title_en="Fix refresh token bug",
            assignee="Sara",
            deadline="tomorrow",
            priority="high",
            context="refresh token bug",
            context_en="Fix refresh token bug before smoke tests",
            detail="Full description of the refresh token bug.",
            acceptance_criteria=["Refresh stable across two tabs"],
        )
        issue = build_issue_payload(task, "Standup", "Sprint standup")
        assert issue.summary == "Fix refresh token bug"
        assert "*Work description:*" in issue.description
        assert "Full description of the refresh token bug." in issue.description
        assert "*Meeting:* Sprint standup" in issue.description
        assert issue.priority == "High"

    def test_missing_optional_fields_use_dash(self):
        task = MeetingTask(title="T", title_en="Task T", context="")
        issue = build_issue_payload(task, "Meeting", "Dev sync")
        assert "*Work description:*\n—" in issue.description
        assert "Suggested assignee" not in issue.description

    def test_unknown_priority_maps_to_medium(self):
        task = MeetingTask(title="T", title_en="T", priority="medium", context="c")
        assert build_issue_payload(task, "x").priority == PRIORITY_MAP["medium"]


class TestPreviewIssues:
    def test_assigns_task_index(self):
        tasks = [
            MeetingTask(title="A", title_en="Task A", context="a", context_en="ctx a"),
            MeetingTask(title="B", title_en="Task B", context="b", context_en="ctx b"),
        ]
        issues = preview_issues(tasks, "Meeting", "Team meeting")
        assert [i.task_index for i in issues] == [0, 1]
        assert issues[0].summary == "Task A"

    def test_empty_tasks(self):
        assert preview_issues([], "Meeting") == []


class TestAuthHeader:
    def test_basic_auth_encoding(self):
        with (
            patch("backend.services.jira.JIRA_EMAIL", "user@test.com"),
            patch("backend.services.jira.JIRA_API_TOKEN", "secret-token"),
        ):
            headers = _auth_header()
            encoded = headers["Authorization"].split(" ", 1)[1]
            decoded = base64.b64decode(encoded).decode()
            assert decoded == "user@test.com:secret-token"


class TestCreateIssues:
    @pytest.mark.asyncio
    async def test_raises_without_credentials(self):
        from backend.models.schemas import JiraPreviewIssue

        issue = JiraPreviewIssue(
            summary="S", description="D", priority="Medium", task_index=0
        )
        with patch("backend.services.jira.JIRA_EMAIL", ""):
            with pytest.raises(ValueError, match="credentials"):
                await create_issues([issue])

    @pytest.mark.asyncio
    async def test_successful_create(self):
        from backend.models.schemas import JiraPreviewIssue

        issue = JiraPreviewIssue(
            summary="Task", description="Desc", priority="High", task_index=0
        )
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"key": "KAN-99"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch("backend.services.jira.JIRA_EMAIL", "u@t.com"),
            patch("backend.services.jira.JIRA_API_TOKEN", "tok"),
            patch("backend.services.jira.httpx.AsyncClient", return_value=mock_client),
        ):
            created = await create_issues([issue])

        assert created == [{"key": "KAN-99", "summary": "Task", "task_index": 0}]
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_jira_error_raises_value_error(self):
        from backend.models.schemas import JiraPreviewIssue

        issue = JiraPreviewIssue(
            summary="T", description="D", priority="Low", task_index=0
        )
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with (
            patch("backend.services.jira.JIRA_EMAIL", "u@t.com"),
            patch("backend.services.jira.JIRA_API_TOKEN", "tok"),
            patch("backend.services.jira.httpx.AsyncClient", return_value=mock_client),
        ):
            with pytest.raises(ValueError, match="Jira error \\(400\\)"):
                await create_issues([issue])
