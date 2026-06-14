from unittest.mock import AsyncMock, patch

import pytest

from backend.services.ingest import ingest_meeting
from backend.tests.conftest import SAMPLE_ANALYSIS, SAMPLE_TRANSCRIPT


class TestIngestMeeting:
    @pytest.mark.asyncio
    async def test_ingest_success(self, meeting_store, vector_store):
        with patch(
            "backend.services.ingest.analyze_transcript",
            new=AsyncMock(return_value=SAMPLE_ANALYSIS),
        ):
            record = await ingest_meeting(
                SAMPLE_TRANSCRIPT,
                title="عنوان سفارشی",
                store=meeting_store,
                vector_store=vector_store,
            )

        assert record.id
        assert record.title == "عنوان سفارشی"
        assert len(record.analysis.tasks) == 2
        assert meeting_store.get(record.id) is not None
        assert len(vector_store.load(record.id)) == 1

    @pytest.mark.asyncio
    async def test_ingest_empty_transcript_raises(self, meeting_store, vector_store):
        with pytest.raises(ValueError, match="نامعتبر"):
            await ingest_meeting("   ", store=meeting_store, vector_store=vector_store)

    @pytest.mark.asyncio
    async def test_ingest_uses_analysis_title_when_no_override(
        self, meeting_store, vector_store
    ):
        with patch(
            "backend.services.ingest.analyze_transcript",
            new=AsyncMock(return_value=SAMPLE_ANALYSIS),
        ):
            record = await ingest_meeting(
                SAMPLE_TRANSCRIPT,
                store=meeting_store,
                vector_store=vector_store,
            )
        assert record.title == SAMPLE_ANALYSIS.title

    @pytest.mark.asyncio
    async def test_ingest_sets_source(self, meeting_store, vector_store):
        with patch(
            "backend.services.ingest.analyze_transcript",
            new=AsyncMock(return_value=SAMPLE_ANALYSIS),
        ):
            record = await ingest_meeting(
                SAMPLE_TRANSCRIPT,
                source="synthetic:demo",
                store=meeting_store,
                vector_store=vector_store,
            )
        assert record.source == "synthetic:demo"
