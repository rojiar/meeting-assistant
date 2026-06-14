"""Meeting transcript statistics."""

from collections import Counter

from backend.services.transcript import parse_transcript


def speaker_participation(transcript: str) -> list[dict[str, object]]:
    turns = parse_transcript(transcript)
    if not turns:
        return []
    counts = Counter(t.speaker for t in turns)
    total = sum(counts.values())
    return [
        {
            "speaker": speaker,
            "turns": count,
            "percent": round(100 * count / total, 1),
        }
        for speaker, count in counts.most_common()
    ]
