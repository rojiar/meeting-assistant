"""Search and export endpoints."""

from backend.services.export import meeting_to_markdown
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT
from backend.models.schemas import MeetingRecord


class TestMeetingSearch:
    def test_search_by_title_keyword(self, meeting_store):
        meeting_store.save(
            MeetingRecord(
                id="s1",
                title="استنداپ دوشنبه",
                transcript=SAMPLE_TRANSCRIPT,
                analysis=SAMPLE_ANALYSIS,
                created_at="2026-05-26T10:00:00+00:00",
            )
        )
        meeting_store.save(
            MeetingRecord(
                id="s2",
                title="برنامه‌ریزی محصول",
                transcript=SAMPLE_TRANSCRIPT,
                analysis=SAMPLE_ANALYSIS.model_copy(
                    update={"summary": "جلسه planning برای Q3"}
                ),
                created_at="2026-05-26T11:00:00+00:00",
            )
        )
        hits = meeting_store.search("استنداپ")
        assert len(hits) == 1
        assert hits[0].id == "s1"

    def test_empty_query_lists_all(self, meeting_store, sample_record):
        assert len(meeting_store.search("")) >= 1


class TestExportMarkdown:
    def test_markdown_contains_sections(self, sample_record):
        md = meeting_to_markdown(sample_record)
        assert "# " in md
        assert "## Summary" in md
        assert "## Tasks" in md
