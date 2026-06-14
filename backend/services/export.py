"""Export meeting analysis as Markdown."""

from backend.models.schemas import MeetingRecord

PRIORITY_LABELS = {"high": "High", "medium": "Medium", "low": "Low"}


def meeting_to_markdown(record: MeetingRecord) -> str:
    a = record.analysis
    lines = [
        f"# {record.title}",
        "",
        f"- **ID:** `{record.id}`",
        f"- **Created:** {record.created_at}",
        f"- **Source:** {record.source}",
        "",
        "## Summary",
        "",
        a.summary,
        "",
    ]
    if a.key_points:
        lines.extend(["## Key points", ""])
        lines.extend(f"- {p}" for p in a.key_points)
        lines.append("")
    if a.decisions:
        lines.extend(["## Decisions", ""])
        lines.extend(f"- {d}" for d in a.decisions)
        lines.append("")
    if a.tasks:
        lines.extend(["## Tasks", ""])
        for i, t in enumerate(a.tasks, 1):
            pr = PRIORITY_LABELS.get(t.priority, t.priority)
            lines.append(f"### {i}. {t.title}")
            if t.title_en and t.title_en != t.title:
                lines.append(f"- **Jira summary:** {t.title_en}")
            if t.assignee:
                lines.append(f"- **Assignee:** {t.assignee}")
            if t.deadline:
                lines.append(f"- **Deadline:** {t.deadline}")
            lines.append(f"- **Priority:** {pr}")
            if t.context:
                lines.append(f"- **Context:** {t.context}")
            if t.detail:
                lines.append(f"- **Detail:** {t.detail}")
            if t.acceptance_criteria:
                lines.append("- **Acceptance criteria:**")
                lines.extend(f"  - {c}" for c in t.acceptance_criteria)
            lines.append("")
    return "\n".join(lines).strip() + "\n"
