import os
import re

from pydantic_ai import Agent

from backend.config import GEMINI_MODEL, GOOGLE_API_KEY
from backend.models.schemas import ChunkCitation, RagAnswer
from backend.services.vector_store import VectorStore

if GOOGLE_API_KEY:
    os.environ.setdefault("GOOGLE_API_KEY", GOOGLE_API_KEY)

# Greetings / chit-chat — no transcript retrieval
_SMALL_TALK_RE = re.compile(
    r"^[\s!?.,]*("
    r"سلام|درود|صبح بخیر|عصر بخیر|hello|hi|hey|howdy|"
    r"thanks|thank you|thx|ممنون|متشکرم|مرسی|"
    r"خداحافظ|bye|goodbye|"
    r"چطوری|چطورید|خوبی|how are you"
    r")[\s!?.,]*$",
    re.IGNORECASE | re.UNICODE,
)

rag_agent = Agent(
    GEMINI_MODEL,
    output_type=RagAnswer,
    system_prompt=(
        "You answer questions about a meeting using ONLY the transcript context provided in the user message. "
        "Reply in English unless the user writes in Persian/Farsi. "
        "Write a natural conversational answer — summarize and paraphrase; never paste long raw transcript blocks. "
        "Weave attributions naturally (e.g. 'Ali said that...'). "
        "In `sources`, include ONLY chunk_ids you actually relied on, each with a short excerpt (max 15 words) — "
        "not the full chunk text. "
        "Set used_meeting_context=true when you used transcript context, false otherwise. "
        "If the answer is not in the context, say 'Not found in this meeting' and leave sources empty."
    ),
)

_chitchat_agent = Agent(
    GEMINI_MODEL,
    output_type=RagAnswer,
    system_prompt=(
        "You are a friendly meeting assistant. The user sent a greeting or small talk, NOT a meeting question. "
        "Reply briefly in English (or match their language). "
        "Invite them to ask about the meeting (decisions, tasks, deadlines). "
        "Set used_meeting_context=false and sources=[]."
    ),
)


def is_small_talk(question: str) -> bool:
    q = question.strip()
    if not q:
        return True
    if _SMALL_TALK_RE.match(q):
        return True
    # Very short non-question utterances
    if len(q) <= 12 and "?" not in q and "؟" not in q:
        return True
    return False


def _build_context_block(chunks) -> str:
    if not chunks:
        return ""
    lines = []
    for chunk in chunks:
        lines.append(f"[{chunk.chunk_id}] {chunk.speaker}: {chunk.text}")
    return "\n".join(lines)


async def ask_meeting(
    meeting_id: str,
    question: str,
    vector_store: VectorStore,
) -> RagAnswer:
    question = question.strip()
    if not question:
        return RagAnswer(
            answer="Please enter a question.",
            sources=[],
            used_meeting_context=False,
        )

    if is_small_talk(question):
        result = await _chitchat_agent.run(f"User message: {question}")
        out = result.output
        out.used_meeting_context = False
        out.sources = []
        return out

    chunks = await vector_store.search(meeting_id, question, top_k=4)
    if not chunks:
        return RagAnswer(
            answer="No relevant information was found in this meeting for that question.",
            sources=[],
            used_meeting_context=True,
        )

    context = _build_context_block(chunks)
    prompt = (
        f"--- Transcript context (internal, do not dump verbatim) ---\n{context}\n"
        f"--- End context ---\n\n"
        f"User question: {question}"
    )
    result = await rag_agent.run(prompt)
    answer = result.output
    answer.used_meeting_context = True

    # Trim source excerpts for UI footnotes only
    trimmed_sources: list[ChunkCitation] = []
    for src in answer.sources:
        excerpt = (src.excerpt or src.text or "").strip()
        if len(excerpt) > 120:
            excerpt = excerpt[:117] + "…"
        trimmed_sources.append(
            ChunkCitation(
                chunk_id=src.chunk_id,
                speaker=src.speaker,
                excerpt=excerpt,
                text=excerpt,
            )
        )
    answer.sources = trimmed_sources
    return answer
