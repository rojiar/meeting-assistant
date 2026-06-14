from backend.agents.facilitation import suggest_facilitation
from backend.models.schemas import FacilitationReport, MeetingRecord
from backend.services.stats import speaker_participation


async def build_facilitation_report(record: MeetingRecord) -> FacilitationReport:
    stats = speaker_participation(record.transcript)
    return await suggest_facilitation(
        transcript=record.transcript,
        analysis=record.analysis,
        meeting_type=record.meeting_type,
        speaker_stats=stats,
    )
