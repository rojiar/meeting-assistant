"""Transcribe meeting audio with Gemini (same GOOGLE_API_KEY as analysis/RAG)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from backend.config import GEMINI_MODEL, GOOGLE_API_KEY, MAX_AUDIO_BYTES
from backend.services.gemini_errors import raise_for_gemini_response
from backend.services.transcript import parse_transcript

TRANSCRIBE_PROMPT = (
    "Listen to this meeting recording and transcribe it in Persian (Farsi).\n"
    "Output ONLY the transcript, one utterance per line, using this exact format:\n"
    "[MM:SS] SpeakerName: spoken text\n\n"
    "Rules:\n"
    "- Use Persian digits for timestamps when natural, or MM:SS in Latin digits.\n"
    "- Infer distinct speakers (use real names if mentioned, otherwise گوینده ۱، گوینده ۲).\n"
    "- Keep filler words minimal but preserve meaning.\n"
    "- Do not add summaries, titles, or commentary."
)

MIME_BY_EXT: dict[str, str] = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}


def gemini_model_id() -> str:
    if GEMINI_MODEL.startswith("google:"):
        return GEMINI_MODEL.removeprefix("google:")
    return GEMINI_MODEL


def resolve_audio_mime(filename: str | None, content_type: str | None) -> str:
    if content_type and content_type.startswith("audio/"):
        return content_type.split(";")[0].strip()
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in MIME_BY_EXT:
            return MIME_BY_EXT[ext]
        guessed, _ = mimetypes.guess_type(filename)
        if guessed and guessed.startswith("audio/"):
            return guessed
    raise ValueError(
        "فرمت صوتی پشتیبانی نمی‌شود. mp3، wav، m4a، ogg، webm یا flac بفرستید."
    )


def validate_audio_payload(data: bytes, mime_type: str) -> None:
    if not data:
        raise ValueError("فایل صوتی خالی است")
    if len(data) > MAX_AUDIO_BYTES:
        max_mb = MAX_AUDIO_BYTES // (1024 * 1024)
        raise ValueError(f"حجم فایل صوتی بیش از {max_mb} مگابایت است")


async def transcribe_audio(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not configured")

    mime_type = resolve_audio_mime(filename, content_type)
    validate_audio_payload(data, mime_type)

    model_id = gemini_model_id()
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(data).decode("ascii"),
                        }
                    },
                    {"text": TRANSCRIBE_PROMPT},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
            params={"key": GOOGLE_API_KEY},
            json=payload,
        )
        raise_for_gemini_response(response)
        body = response.json()

    text = _extract_text(body).strip()
    if not text:
        raise ValueError("Gemini متن transcript برنگرداند")

    turns = parse_transcript(text)
    if not turns:
        raise ValueError(
            "خروجی رونویسی قابل parse نیست — دوباره ضبط کنید یا متن را دستی ویرایش کنید"
        )

    return text


def _extract_text(body: dict) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    return "\n".join(chunks)
