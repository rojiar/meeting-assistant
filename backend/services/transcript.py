import re

from backend.models.schemas import TranscriptChunk, TranscriptTurn

TURN_PATTERN = re.compile(
    r"^\[([^\]]+)\]\s*([^:：]+)[:：]\s*(.+)$",
    re.MULTILINE,
)

CHUNK_SIZE = 4


def parse_transcript(text: str) -> list[TranscriptTurn]:
    turns: list[TranscriptTurn] = []
    for match in TURN_PATTERN.finditer(text.strip()):
        turns.append(
            TranscriptTurn(
                timestamp=match.group(1).strip(),
                speaker=match.group(2).strip(),
                text=match.group(3).strip(),
            )
        )

    if not turns and text.strip():
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                speaker, _, content = line.partition(":")
                turns.append(
                    TranscriptTurn(
                        timestamp="",
                        speaker=speaker.strip() or "ناشناس",
                        text=content.strip(),
                    )
                )
            else:
                turns.append(TranscriptTurn(timestamp="", speaker="ناشناس", text=line))
    return turns


def chunk_transcript(turns: list[TranscriptTurn]) -> list[TranscriptChunk]:
    if not turns:
        return []

    chunks: list[TranscriptChunk] = []
    for start in range(0, len(turns), CHUNK_SIZE):
        group = turns[start : start + CHUNK_SIZE]
        speakers = {t.speaker for t in group}
        speaker_label = group[0].speaker if len(speakers) == 1 else "چند نفر"
        lines = []
        for turn in group:
            prefix = f"[{turn.timestamp}] " if turn.timestamp else ""
            lines.append(f"{prefix}{turn.speaker}: {turn.text}")
        chunks.append(
            TranscriptChunk(
                chunk_id=f"c{len(chunks)}",
                speaker=speaker_label,
                text="\n".join(lines),
                turn_indices=list(range(start, start + len(group))),
            )
        )
    return chunks


def format_transcript(turns: list[TranscriptTurn]) -> str:
    lines = []
    for turn in turns:
        ts = f"[{turn.timestamp}] " if turn.timestamp else ""
        lines.append(f"{ts}{turn.speaker}: {turn.text}")
    return "\n".join(lines)
