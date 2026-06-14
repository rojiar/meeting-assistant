"""Pydantic Logfire setup for LLM/agent and API observability (MLOps)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from backend.config import (
    LOGFIRE_ENVIRONMENT,
    LOGFIRE_SERVICE_NAME,
    LOGFIRE_TOKEN,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

_configured = False


def configure_observability(app: FastAPI | None = None) -> bool:
    """Initialize Logfire once; instrument Pydantic AI, HTTPX, and optionally FastAPI."""
    global _configured

    if app is not None and _configured:
        _instrument_fastapi(app)
        return bool(LOGFIRE_TOKEN)

    if _configured:
        return bool(LOGFIRE_TOKEN)

    import logfire

    send_mode = "if-token-present" if LOGFIRE_TOKEN else False
    logfire.configure(
        send_to_logfire=send_mode,
        token=LOGFIRE_TOKEN or None,
        service_name=LOGFIRE_SERVICE_NAME,
        service_version=os.getenv("APP_VERSION", "0.2.0"),
        environment=LOGFIRE_ENVIRONMENT,
        inspect_arguments=False,
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
    _configured = True

    if app is not None:
        _instrument_fastapi(app)

    return bool(LOGFIRE_TOKEN)


def _instrument_fastapi(app: FastAPI) -> None:
    import logfire

    logfire.instrument_fastapi(app)


def span(name: str, /, **attributes):
    """Safe span helper for pipeline code; no-op if Logfire is unavailable."""
    import logfire

    return logfire.span(name, **attributes)
