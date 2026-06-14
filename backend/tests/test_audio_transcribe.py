from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.audio_transcribe import (
    resolve_audio_mime,
    transcribe_audio,
    validate_audio_payload,
)


class TestResolveAudioMime:
    def test_by_extension(self):
        assert resolve_audio_mime("meeting.mp3", None) == "audio/mp3"

    def test_by_content_type(self):
        assert resolve_audio_mime("x.bin", "audio/wav; charset=binary") == "audio/wav"

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="پشتیبانی نمی‌شود"):
            resolve_audio_mime("notes.pdf", "application/pdf")


class TestValidateAudioPayload:
    def test_empty_raises(self):
        with pytest.raises(ValueError, match="خالی"):
            validate_audio_payload(b"", "audio/mp3")

    def test_too_large_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("backend.services.audio_transcribe.MAX_AUDIO_BYTES", 10)
        with pytest.raises(ValueError, match="مگابایت"):
            validate_audio_payload(b"x" * 11, "audio/mp3")


class TestTranscribeAudio:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "backend.services.audio_transcribe.GOOGLE_API_KEY", "test-key"
        )
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "[۰۹:۰۰] علی: صبح بخیر\n[۰۹:۰۱] سارا: تست auth"}
                        ]
                    }
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "backend.services.audio_transcribe.httpx.AsyncClient",
            return_value=mock_client,
        ):
            text = await transcribe_audio(b"fake-audio", filename="a.mp3")

        assert "[۰۹:۰۰] علی:" in text
        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        with patch("backend.services.audio_transcribe.GOOGLE_API_KEY", ""):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                await transcribe_audio(b"x", filename="a.mp3")


class TestTranscribeApi:
    @pytest.fixture
    def client(self, meeting_store, vector_store, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("backend.main.meeting_store", meeting_store)
        monkeypatch.setattr("backend.main.vector_store", vector_store)
        return TestClient(app)

    def test_transcribe_success(self, client: TestClient):
        with patch(
            "backend.main.transcribe_audio",
            new=AsyncMock(return_value="[۰۹:۰۰] علی: hi"),
        ):
            response = client.post(
                "/api/transcribe",
                files={"file": ("meeting.mp3", b"audio-bytes", "audio/mp3")},
            )
        assert response.status_code == 200
        assert "علی" in response.json()["transcript"]

    def test_transcribe_value_error_400(self, client: TestClient):
        with patch(
            "backend.main.transcribe_audio",
            new=AsyncMock(side_effect=ValueError("bad audio")),
        ):
            response = client.post(
                "/api/transcribe",
                files={"file": ("x.mp3", b"x", "audio/mp3")},
            )
        assert response.status_code == 400
