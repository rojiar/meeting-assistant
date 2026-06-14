"""Shared Pydantic schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class MeetingTask(BaseModel):
    title: str
    title_en: str = ""
    assignee: str | None = None
    deadline: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    context: str = ""
    context_en: str = ""
    detail: str = ""
    detail_en: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    acceptance_criteria_en: list[str] = Field(default_factory=list)
    jira_key: str | None = None


class MeetingAnalysis(BaseModel):
    title: str
    title_en: str = ""
    summary: str
    key_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    tasks: list[MeetingTask] = Field(default_factory=list)


class ChunkCitation(BaseModel):
    chunk_id: str
    speaker: str
    excerpt: str = ""
    text: str = ""  # alias for excerpt (backward compat)


class RagAnswer(BaseModel):
    answer: str
    sources: list[ChunkCitation] = Field(default_factory=list)
    used_meeting_context: bool = False


class TranscriptTurn(BaseModel):
    timestamp: str
    speaker: str
    text: str


class TranscriptChunk(BaseModel):
    chunk_id: str
    speaker: str
    text: str
    turn_indices: list[int]


MeetingType = Literal["general", "standup", "planning", "review"]


class MeetingRecord(BaseModel):
    id: str
    title: str
    transcript: str
    analysis: MeetingAnalysis
    created_at: str
    source: str = "upload"
    meeting_type: MeetingType = "general"
    tags: list[str] = Field(default_factory=list)
    project_key: str = ""


class CreateMeetingRequest(BaseModel):
    transcript: str
    title: str | None = None
    meeting_type: MeetingType = "general"
    tags: list[str] = Field(default_factory=list)
    project_key: str = ""


class UpdateMeetingRequest(BaseModel):
    title: str | None = None
    tags: list[str] | None = None
    project_key: str | None = None
    meeting_type: MeetingType | None = None


class SpeakerJiraMap(BaseModel):
    speaker_name: str
    jira_account_id: str
    jira_display_name: str = ""


class ActionItem(BaseModel):
    meeting_id: str
    meeting_title: str
    meeting_type: MeetingType = "general"
    project_key: str = ""
    task_index: int
    title: str
    title_en: str = ""
    assignee: str | None = None
    deadline: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    jira_key: str | None = None


class SpeakerStat(BaseModel):
    speaker: str
    turns: int
    percent: float


class AskRequest(BaseModel):
    question: str


class TranscribeResponse(BaseModel):
    transcript: str


class FacilitationReport(BaseModel):
    what_went_well: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_meeting_agenda: list[str] = Field(default_factory=list)
    timebox_suggestion: str = ""
    coaching_summary: str = ""
    facilitator_score: int | None = Field(default=None, ge=1, le=5)


class JiraPreviewIssue(BaseModel):
    summary: str
    description: str
    priority: str
    task_index: int


class JiraCreateRequest(BaseModel):
    task_indices: list[int] | None = None
