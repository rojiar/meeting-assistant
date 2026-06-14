import os

from pydantic_ai import Agent

from backend.config import GEMINI_MODEL, GOOGLE_API_KEY
from backend.models.schemas import MeetingAnalysis, MeetingType

if GOOGLE_API_KEY:
    os.environ.setdefault("GOOGLE_API_KEY", GOOGLE_API_KEY)

BASE_PROMPT = (
    "You analyze meeting transcripts (often in Persian/Farsi). "
    "Output ALL UI fields in English: title, summary, key_points, decisions, and each task's "
    "title, context, detail, and acceptance_criteria. "
    "Also output title_en (meeting) and per task title_en / context_en for Jira — keep them "
    "concise and professional in English (they may mirror the English UI fields). "
    "For every task, also output detail_en and acceptance_criteria_en as English equivalents. "
    "context must stay a one-line summary; detail must add real information beyond context. "
    "Tasks must be actionable. Priority: high, medium, or low."
)

MEETING_TYPE_HINTS: dict[MeetingType, str] = {
    "standup": (
        "This is a daily standup. Focus on: what each person did, blockers, "
        "today's plan. Keep summary short. Tasks = concrete next steps with owners."
    ),
    "planning": (
        "This is a sprint/quarter planning session. Focus on: scope, milestones, "
        "deadlines, dependencies, and explicit decisions. Tasks should map to deliverables."
    ),
    "review": (
        "This is a review/retro/demo session. Focus on: outcomes, feedback, "
        "lessons learned, and follow-up actions. Capture decisions clearly."
    ),
    "general": "",
}

analysis_agent = Agent(
    GEMINI_MODEL,
    output_type=MeetingAnalysis,
    system_prompt=BASE_PROMPT,
)


async def analyze_transcript(
    transcript: str, meeting_type: MeetingType = "general"
) -> MeetingAnalysis:
    hint = MEETING_TYPE_HINTS.get(meeting_type, "")
    prompt = f"Meeting type: {meeting_type}\n\nAnalyze this transcript:\n\n{transcript}"
    if hint:
        prompt += f"\n\nGuidance: {hint}"
    result = await analysis_agent.run(prompt)
    return result.output
