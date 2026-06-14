"""Map Google Gemini / Pydantic AI errors to user-friendly English HTTP responses."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from pydantic_ai.exceptions import ModelHTTPError


def extract_google_error_message(body: object | None) -> str:
    if body is None:
        return ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
            status = error.get("status")
            if isinstance(status, str):
                return status
        message = body.get("message")
        if isinstance(message, str):
            return message
    return str(body)


def parse_gemini_error(exc: Exception) -> tuple[int, str] | None:
    if isinstance(exc, ModelHTTPError):
        return exc.status_code, extract_google_error_message(exc.body)

    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body: Any = exc.response.json()
        except ValueError:
            body = exc.response.text
        message = (
            extract_google_error_message(body) if isinstance(body, dict) else str(body)
        )
        return exc.response.status_code, message

    return None


def classify_gemini_http_error(status_code: int, message: str) -> tuple[int, str]:
    msg_lower = message.lower()

    if status_code == 403 and (
        "dunning" in msg_lower or "lightning dunning" in msg_lower
    ):
        return (
            403,
            "Gemini access denied: billing may be disabled or overdue for this Google "
            "Cloud / AI Studio project. Check billing in Google AI Studio or Cloud Console.",
        )

    if status_code == 401 or "api key" in msg_lower or "unauthenticated" in msg_lower:
        return (
            401,
            "Invalid or missing Google API key. Check GOOGLE_API_KEY in .env.",
        )

    if status_code == 429 or "quota" in msg_lower or "rate limit" in msg_lower:
        return (
            429,
            "Gemini quota or rate limit exceeded. Try again shortly.",
        )

    if status_code == 403:
        return (
            403,
            "Gemini access denied. Check API key, billing, and model permissions.",
        )

    if status_code == 404 or "not found" in msg_lower:
        return (
            502,
            "Configured Gemini model was not found. Check GEMINI_MODEL in .env.",
        )

    if status_code >= 500:
        return (
            502,
            "Gemini is temporarily unavailable. Try again later.",
        )

    return (
        502,
        f"Gemini request failed ({status_code}): {message or 'unknown error'}",
    )


def http_exception_from_gemini_error(
    exc: Exception, *, context: str = "processing"
) -> HTTPException:
    parsed = parse_gemini_error(exc)
    if parsed is None:
        return HTTPException(
            status_code=502,
            detail=f"Error during {context}: {exc}",
        )

    status_code, message = parsed
    http_status, detail = classify_gemini_http_error(status_code, message)
    return HTTPException(status_code=http_status, detail=detail)


def raise_for_gemini_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    message = (
        extract_google_error_message(body) if isinstance(body, dict) else str(body)
    )
    http_status, detail = classify_gemini_http_error(response.status_code, message)
    raise HTTPException(status_code=http_status, detail=detail)
