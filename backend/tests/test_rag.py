import pytest

from backend.agents.rag import is_small_talk, ask_meeting
from backend.models.schemas import ChunkCitation, RagAnswer
from backend.services.vector_store import StoredChunk, VectorStore
from backend.tests.conftest import FakeEmbeddingService
from unittest.mock import AsyncMock, MagicMock, patch


class TestIsSmallTalk:
    @pytest.mark.parametrize(
        "msg",
        ["hello", "Hello!", "سلام", "Hi", "ممنون", "thanks", "  hey  "],
    )
    def test_greetings_detected(self, msg: str):
        assert is_small_talk(msg) is True

    @pytest.mark.parametrize(
        "msg",
        ["deadline release چیست؟", "چه تصمیمی گرفتیم؟", "Who owns the API docs?"],
    )
    def test_meeting_questions_not_small_talk(self, msg: str):
        assert is_small_talk(msg) is False


class TestAskMeeting:
    @pytest.mark.asyncio
    async def test_hello_uses_chitchat_no_sources(self, tmp_data_dirs):
        store = VectorStore(tmp_data_dirs["chroma"], FakeEmbeddingService())
        mock_answer = RagAnswer(
            answer="سلام! درباره جلسه بپرسید.",
            sources=[],
            used_meeting_context=False,
        )
        mock_result = MagicMock()
        mock_result.output = mock_answer

        with patch(
            "backend.agents.rag._chitchat_agent.run",
            new=AsyncMock(return_value=mock_result),
        ) as mock_run:
            answer = await ask_meeting("m1", "hello", store)

        mock_run.assert_called_once()
        assert answer.sources == []
        assert answer.used_meeting_context is False

    @pytest.mark.asyncio
    async def test_meeting_question_injects_context(self, tmp_data_dirs):
        store = VectorStore(tmp_data_dirs["chroma"], FakeEmbeddingService())
        from backend.models.schemas import TranscriptChunk

        await store.index_meeting(
            "m2",
            [
                TranscriptChunk(
                    chunk_id="c0",
                    speaker="Ali",
                    text="deadline Friday",
                    turn_indices=[0],
                )
            ],
        )

        mock_answer = RagAnswer(
            answer="Ali said the deadline is Friday.",
            sources=[
                ChunkCitation(
                    chunk_id="c0",
                    speaker="Ali",
                    excerpt="deadline Friday",
                )
            ],
            used_meeting_context=True,
        )
        mock_result = MagicMock()
        mock_result.output = mock_answer

        with patch(
            "backend.agents.rag.rag_agent.run", new=AsyncMock(return_value=mock_result)
        ) as mock_run:
            answer = await ask_meeting("m2", "when is the deadline?", store)

        assert "Transcript context" in mock_run.call_args[0][0]
        assert answer.used_meeting_context is True
        assert answer.sources[0].excerpt == "deadline Friday"
        assert len(answer.sources[0].excerpt) <= 120

    @pytest.mark.asyncio
    async def test_no_chunks_returns_not_found(self, tmp_data_dirs):
        store = VectorStore(tmp_data_dirs["chroma"], FakeEmbeddingService())
        answer = await ask_meeting("missing", "deadline?", store)
        assert (
            "No relevant information" in answer.answer
            or "not found" in answer.answer.lower()
        )
        assert answer.sources == []
