from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_observability():
    import backend.observability as obs

    obs._configured = False
    yield
    obs._configured = False


class TestConfigureObservability:
    def test_configures_without_token(self):
        import backend.observability as obs

        mock_logfire = MagicMock()
        with (
            patch("backend.observability.LOGFIRE_TOKEN", ""),
            patch("backend.observability.LOGFIRE_SERVICE_NAME", "meeting-assistant"),
            patch("backend.observability.LOGFIRE_ENVIRONMENT", "test"),
            patch("logfire.configure", mock_logfire.configure, create=True),
            patch(
                "logfire.instrument_pydantic_ai",
                mock_logfire.instrument_pydantic_ai,
                create=True,
            ),
            patch(
                "logfire.instrument_httpx", mock_logfire.instrument_httpx, create=True
            ),
        ):
            enabled = obs.configure_observability()
            assert enabled is False
            mock_logfire.configure.assert_called_once()
            assert mock_logfire.configure.call_args.kwargs["send_to_logfire"] is False
            mock_logfire.instrument_pydantic_ai.assert_called_once()
            mock_logfire.instrument_httpx.assert_called_once_with(capture_all=True)

            obs.configure_observability()
            assert mock_logfire.configure.call_count == 1

    def test_instruments_fastapi_when_app_provided(self):
        import backend.observability as obs

        mock_logfire = MagicMock()
        mock_app = MagicMock()
        with (
            patch("backend.observability.LOGFIRE_TOKEN", "tok"),
            patch("logfire.configure", mock_logfire.configure, create=True),
            patch(
                "logfire.instrument_pydantic_ai",
                mock_logfire.instrument_pydantic_ai,
                create=True,
            ),
            patch(
                "logfire.instrument_httpx", mock_logfire.instrument_httpx, create=True
            ),
            patch(
                "logfire.instrument_fastapi",
                mock_logfire.instrument_fastapi,
                create=True,
            ),
        ):
            enabled = obs.configure_observability(mock_app)
            assert enabled is True
            mock_logfire.instrument_fastapi.assert_called_once_with(mock_app)
