import pytest

from backend.services.transcript import (
    CHUNK_SIZE,
    chunk_transcript,
    format_transcript,
    parse_transcript,
)


class TestParseTranscript:
    def test_persian_timestamp_and_speaker(self):
        text = "[۰۹:۰۰] علی: سلام\n[۰۹:۰۱] سارا: تست"
        turns = parse_transcript(text)
        assert len(turns) == 2
        assert turns[0].speaker == "علی"
        assert turns[0].timestamp == "۰۹:۰۰"
        assert "سلام" in turns[0].text

    def test_ascii_timestamp(self):
        text = "[09:00] Ali: hello"
        turns = parse_transcript(text)
        assert turns[0].speaker == "Ali"

    def test_persian_colon_separator(self):
        text = "[۱۰:۰۰] مدیر：تصمیم گرفتیم"
        turns = parse_transcript(text)
        assert turns[0].speaker == "مدیر"

    def test_fallback_line_without_brackets(self):
        text = "علی: بدون timestamp\nسارا: خط دوم"
        turns = parse_transcript(text)
        assert len(turns) == 2
        assert turns[0].speaker == "علی"

    def test_fallback_unlabeled_line_gets_unknown_speaker(self):
        turns = parse_transcript("فقط یک جمله بدون speaker")
        assert len(turns) == 1
        assert turns[0].speaker == "ناشناس"

    def test_empty_string_returns_empty(self):
        assert parse_transcript("") == []
        assert parse_transcript("   \n  ") == []

    def test_ignores_blank_lines_in_fallback(self):
        text = "علی: اول\n\n\nسارا: دوم"
        turns = parse_transcript(text)
        assert len(turns) == 2


class TestChunkTranscript:
    def test_groups_by_chunk_size(self):
        text = "\n".join(f"[۰۹:{i:02d}] شخص: جمله {i}" for i in range(6))
        turns = parse_transcript(text)
        chunks = chunk_transcript(turns)
        assert len(chunks) == 2
        assert chunks[0].chunk_id == "c0"
        assert chunks[1].chunk_id == "c1"

    def test_single_turn(self):
        turns = parse_transcript("[۰۹:۰۰] علی: تنها turn")
        chunks = chunk_transcript(turns)
        assert len(chunks) == 1
        assert chunks[0].speaker == "علی"

    def test_exact_chunk_boundary(self):
        lines = "\n".join(f"[۰۹:{i:02d}] a: x{i}" for i in range(CHUNK_SIZE))
        chunks = chunk_transcript(parse_transcript(lines))
        assert len(chunks) == 1

    def test_multi_speaker_chunk_label(self):
        lines = "\n".join(f"[۰۹:۰{i}] p{i}: txt" for i in range(3))
        chunk = chunk_transcript(parse_transcript(lines))[0]
        assert chunk.speaker == "چند نفر"

    def test_empty_turns_returns_empty(self):
        assert chunk_transcript([]) == []

    def test_turn_indices_preserved(self):
        turns = parse_transcript("[۰۹:۰۰] a: one\n[۰۹:۰۱] b: two")
        chunk = chunk_transcript(turns)[0]
        assert chunk.turn_indices == [0, 1]


class TestFormatTranscript:
    def test_roundtrip_preserves_speakers(self):
        original = "[۰۹:۰۰] علی: سلام\n[۰۹:۰۱] سارا: خداحافظ"
        turns = parse_transcript(original)
        formatted = format_transcript(turns)
        reparsed = parse_transcript(formatted)
        assert [t.speaker for t in reparsed] == ["علی", "سارا"]

    def test_includes_timestamp_when_present(self):
        turns = parse_transcript("[۰۹:۰۰] علی: hi")
        assert "[۰۹:۰۰]" in format_transcript(turns)
