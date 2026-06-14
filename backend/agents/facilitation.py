import os

from pydantic_ai import Agent

from backend.config import GEMINI_MODEL, GOOGLE_API_KEY
from backend.models.schemas import FacilitationReport, MeetingAnalysis, MeetingType

if GOOGLE_API_KEY:
    os.environ.setdefault("GOOGLE_API_KEY", GOOGLE_API_KEY)

FACILITATION_PROMPT = (
    "You are a meeting facilitation coach for organizational meetings. "
    "Analyze the transcript, summary, decisions, tasks, and speaker participation stats. "
    "Write ALL output fields in English with a supportive coaching tone — never blame individuals. "
    "Focus on how the organizer can run the NEXT meeting more efficiently. "
    "what_went_well: 2-4 concrete positives. "
    "improvements: 2-4 actionable suggestions (timeboxing, agenda, participation balance). "
    "next_meeting_agenda: 3-6 bullet items derived from open tasks and unresolved topics. "
    "timebox_suggestion: one short paragraph on recommended duration and segment timing. "
    "coaching_summary: 2-3 sentences tying it together. "
    "facilitator_score: integer 1-5 for meeting effectiveness (5 = excellent). "
    "Do not invent facts not supported by the transcript or analysis."
)

facilitation_agent = Agent(
    GEMINI_MODEL,
    output_type=FacilitationReport,
    system_prompt=FACILITATION_PROMPT,
)


async def suggest_facilitation(
    *,
    transcript: str,
    analysis: MeetingAnalysis,
    meeting_type: MeetingType,
    speaker_stats: list[dict[str, object]],
) -> FacilitationReport:
    stats_lines = [
        f"- {s['speaker']}: {s['turns']} turns ({s['percent']}%)" for s in speaker_stats
    ]
    decisions = "\n".join(f"- {d}" for d in analysis.decisions) or "—"
    tasks = (
        "\n".join(f"- {t.title} ({t.assignee or 'unassigned'})" for t in analysis.tasks)
        or "—"
    )
    key_points = "\n".join(f"- {p}" for p in analysis.key_points) or "—"

    prompt = f"""Meeting type: {meeting_type}

Summary:
{analysis.summary}

Key points:
{key_points}

Decisions:
{decisions}

Tasks:
{tasks}

Speaker participation:
{chr(10).join(stats_lines) or "—"}

Transcript (for detail):
{transcript}
"""
    result = await facilitation_agent.run(prompt)
    return result.output
