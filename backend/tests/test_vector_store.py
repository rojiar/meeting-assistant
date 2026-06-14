import pytest

from backend.services.vector_store import VectorStore
from backend.tests.conftest import FakeEmbeddingService


class TestVectorStoreChroma:
    @pytest.mark.asyncio
    async def test_index_and_load(self, vector_store: VectorStore, sample_chunks):
        await vector_store.index_meeting("m1", sample_chunks)
        loaded = vector_store.load("m1")
        assert len(loaded) == 3
        assert loaded[0].chunk_id == "c0"

    def test_load_missing_meeting_returns_empty(self, vector_store: VectorStore):
        assert vector_store.load("nonexistent") == []

    @pytest.mark.asyncio
    async def test_reindex_replaces_old_chunks(self, vector_store: VectorStore, sample_chunks):
        await vector_store.index_meeting("m2", sample_chunks[:1])
        await vector_store.index_meeting("m2", sample_chunks)
        assert len(vector_store.load("m2")) == 3

    @pytest.mark.asyncio
    async def test_search_returns_top_k(self, vector_store: VectorStore, sample_chunks):
        await vector_store.index_meeting("m3", sample_chunks)
        results = await vector_store.search("m3", "deadline release پنجشنبه", top_k=2)
        assert len(results) <= 2
        assert results[0].speaker

    @pytest.mark.asyncio
    async def test_search_empty_meeting(self, vector_store: VectorStore):
        results = await vector_store.search("missing", "query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_prefers_relevant_chunk(self, vector_store: VectorStore):
        from backend.models.schemas import TranscriptChunk

        chunks = [
            TranscriptChunk(chunk_id="c0", speaker="a", text="alpha unrelated", turn_indices=[0]),
            TranscriptChunk(chunk_id="c1", speaker="b", text="deadline Friday release", turn_indices=[1]),
        ]
        await vector_store.index_meeting("m4", chunks)
        results = await vector_store.search("m4", "deadline Friday", top_k=1)
        assert "deadline" in results[0].text.lower() or "Friday" in results[0].text
