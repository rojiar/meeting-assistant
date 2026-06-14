from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.observability import configure_observability

configure_observability()

from backend.agents.rag import ask_meeting
from backend.config import (
    GOOGLE_API_KEY,
    JIRA_API_TOKEN,
    JIRA_EMAIL,
    JIRA_SITE_URL,
    CHROMA_DIR,
    LOGFIRE_TOKEN,
    SQLITE_PATH,
)
from backend.models.schemas import (
    ActionItem,
    AskRequest,
    CreateMeetingRequest,
    FacilitationReport,
    JiraCreateRequest,
    MeetingRecord,
    MeetingType,
    SpeakerJiraMap,
    SpeakerStat,
    TranscribeResponse,
    UpdateMeetingRequest,
)
from backend.services.assignee_map import AssigneeMapStore
from backend.services.audio_transcribe import transcribe_audio
from backend.services.export import meeting_to_markdown
from backend.services.facilitation import build_facilitation_report
from backend.services.ingest import ingest_meeting
from backend.services.jira import create_issues, preview_issues
from backend.services.meeting_store import MeetingStore
from backend.services.stats import speaker_participation
from backend.services.gemini_errors import http_exception_from_gemini_error
from backend.services.vector_store import VectorStore

app = FastAPI(title="Meeting Assistant", version="0.2.0")

configure_observability(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://127.0.0.1:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

meeting_store = MeetingStore(SQLITE_PATH)
vector_store = VectorStore(CHROMA_DIR)
assignee_map = AssigneeMapStore(SQLITE_PATH)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "google_api": bool(GOOGLE_API_KEY),
        "jira_configured": bool(JIRA_EMAIL and JIRA_API_TOKEN),
        "jira_site": JIRA_SITE_URL,
        "database": str(SQLITE_PATH),
        "logfire": bool(LOGFIRE_TOKEN),
    }


@app.get("/api/meetings")
async def list_meetings(
    q: str | None = Query(None, description="Search title and summary"),
    type: MeetingType | None = Query(None, alias="type"),
    project: str | None = Query(None),
    tag: str | None = Query(None),
) -> list[MeetingRecord]:
    if q and q.strip():
        return meeting_store.search(
            q.strip(), meeting_type=type, project_key=project, tag=tag
        )
    return meeting_store.list_all(meeting_type=type, project_key=project, tag=tag)


@app.get("/api/tasks", response_model=list[ActionItem])
async def list_tasks(
    open_only: bool = Query(False, description="Only tasks without a Jira key"),
) -> list[ActionItem]:
    return meeting_store.list_action_items(open_only=open_only)


@app.get("/api/meetings/synthetic")
async def list_synthetic() -> list[dict[str, str]]:
    return meeting_store.list_synthetic()


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_meeting_audio(
    file: UploadFile = File(..., description="Meeting audio file"),
) -> TranscribeResponse:
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=400, detail="GOOGLE_API_KEY is not configured")
    try:
        data = await file.read()
        transcript = await transcribe_audio(
            data,
            filename=file.filename,
            content_type=file.content_type,
        )
        return TranscribeResponse(transcript=transcript)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise http_exception_from_gemini_error(
            exc, context="audio transcription"
        ) from exc


@app.post("/api/meetings/synthetic/{file_id}", response_model=MeetingRecord)
async def create_from_synthetic(file_id: str) -> MeetingRecord:
    try:
        transcript = meeting_store.load_synthetic(file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return await ingest_meeting(
            transcript,
            source=f"synthetic:{file_id}",
            store=meeting_store,
            vector_store=vector_store,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise http_exception_from_gemini_error(exc, context="processing") from exc


@app.post("/api/meetings", response_model=MeetingRecord)
async def create_meeting(body: CreateMeetingRequest) -> MeetingRecord:
    if not body.transcript.strip():
        raise HTTPException(status_code=400, detail="transcript is required")
    try:
        return await ingest_meeting(
            body.transcript,
            title=body.title,
            meeting_type=body.meeting_type,
            tags=body.tags,
            project_key=body.project_key,
            store=meeting_store,
            vector_store=vector_store,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise http_exception_from_gemini_error(exc, context="processing") from exc


@app.get("/api/meetings/{meeting_id}/export")
async def export_meeting(meeting_id: str) -> PlainTextResponse:
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    md = meeting_to_markdown(record)
    filename = f"meeting-{meeting_id}.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/meetings/{meeting_id}/speakers", response_model=list[SpeakerStat])
async def meeting_speakers(meeting_id: str) -> list[SpeakerStat]:
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    stats = speaker_participation(record.transcript)
    return [SpeakerStat(**s) for s in stats]


@app.get("/api/meetings/{meeting_id}/facilitation", response_model=FacilitationReport)
async def meeting_facilitation(meeting_id: str) -> FacilitationReport:
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        return await build_facilitation_report(record)
    except Exception as exc:
        raise http_exception_from_gemini_error(
            exc, context="facilitation guide"
        ) from exc


@app.get("/api/meetings/{meeting_id}", response_model=MeetingRecord)
async def get_meeting(meeting_id: str) -> MeetingRecord:
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return record


@app.patch("/api/meetings/{meeting_id}", response_model=MeetingRecord)
async def update_meeting(meeting_id: str, body: UpdateMeetingRequest) -> MeetingRecord:
    record = meeting_store.update(meeting_id, body)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return record


@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str) -> dict:
    if not meeting_store.get(meeting_id):
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting_store.delete(meeting_id)
    vector_store.delete_meeting(meeting_id)
    return {"deleted": meeting_id}


@app.post("/api/meetings/{meeting_id}/ask")
async def ask_question(meeting_id: str, body: AskRequest):
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    try:
        answer = await ask_meeting(meeting_id, body.question, vector_store)
        return answer
    except Exception as exc:
        raise http_exception_from_gemini_error(exc, context="RAG") from exc


@app.post("/api/meetings/{meeting_id}/jira/preview")
async def jira_preview(meeting_id: str):
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")
    issues = preview_issues(
        record.analysis.tasks,
        record.title,
        record.analysis.title_en,
    )
    return {"issues": issues}


@app.post("/api/meetings/{meeting_id}/jira/create")
async def jira_create(meeting_id: str, body: JiraCreateRequest | None = None):
    record = meeting_store.get(meeting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meeting not found")

    issues = preview_issues(
        record.analysis.tasks,
        record.title,
        record.analysis.title_en,
    )
    if body and body.task_indices is not None:
        selected = [issues[i] for i in body.task_indices if 0 <= i < len(issues)]
    else:
        selected = issues

    if not selected:
        raise HTTPException(status_code=400, detail="No tasks selected to send")

    assignee_ids = [
        assignee_map.resolve_account_id(
            record.analysis.tasks[issue.task_index].assignee
        )
        for issue in selected
    ]

    try:
        created = await create_issues(selected, assignee_account_ids=assignee_ids)
        for item in created:
            idx = item.get("task_index")
            key = item.get("key")
            if idx is not None and key:
                meeting_store.update_task_jira_keys(meeting_id, idx, key)
        return {"created": created}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jira error: {exc}") from exc


# --- Assignee mapping (Sprint 3 lite) ---


@app.get("/api/settings/assignee-map", response_model=list[SpeakerJiraMap])
async def list_assignee_map() -> list[SpeakerJiraMap]:
    return assignee_map.list_all()


@app.put("/api/settings/assignee-map", response_model=SpeakerJiraMap)
async def upsert_assignee_map(entry: SpeakerJiraMap) -> SpeakerJiraMap:
    if not entry.speaker_name.strip() or not entry.jira_account_id.strip():
        raise HTTPException(
            status_code=400, detail="speaker name and accountId are required"
        )
    return assignee_map.upsert(entry)


@app.delete("/api/settings/assignee-map/{speaker_name}")
async def delete_assignee_map(speaker_name: str) -> dict:
    if not assignee_map.delete(speaker_name):
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"deleted": speaker_name}
