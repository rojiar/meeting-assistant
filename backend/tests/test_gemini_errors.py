import httpx
import pytest
from fastapi import HTTPException
from pydantic_ai.exceptions import ModelHTTPError

from backend.services.gemini_errors import (
    classify_gemini_http_error,
    extract_google_error_message,
    http_exception_from_gemini_error,
    parse_gemini_error,
    raise_for_gemini_response,
)


DUNNING_BODY = {
    "error": {
        "code": 403,
        "message": "Lightning dunning decision is deny for project: projects/390415010751",
        "status": "PERMISSION_DENIED",
    }
}


class TestExtractGoogleErrorMessage:
    def test_nested_error_message(self):
        assert (
            extract_google_error_message(DUNNING_BODY)
            == DUNNING_BODY["error"]["message"]
        )

    def test_empty_body(self):
        assert extract_google_error_message(None) == ""


class TestParseGeminiError:
    def test_model_http_error_dunning(self):
        exc = ModelHTTPError(
            status_code=403,
            model_name="gemini-2.5-flash",
            body=DUNNING_BODY,
        )
        assert parse_gemini_error(exc) == (403, DUNNING_BODY["error"]["message"])

    def test_httpx_status_error(self):
        request = httpx.Request("POST", "https://example.com")
        response = httpx.Response(
            401,
            request=request,
            json={"error": {"message": "API key not valid"}},
        )
        exc = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
        assert parse_gemini_error(exc) == (401, "API key not valid")

    def test_unrelated_exception_returns_none(self):
        assert parse_gemini_error(RuntimeError("boom")) is None


class TestClassifyGeminiHttpError:
    def test_dunning_403(self):
        status, detail = classify_gemini_http_error(
            403, DUNNING_BODY["error"]["message"]
        )
        assert status == 403
        assert "billing" in detail

    def test_invalid_api_key(self):
        status, detail = classify_gemini_http_error(401, "API key not valid")
        assert status == 401
        assert "GOOGLE_API_KEY" in detail

    def test_rate_limit(self):
        status, detail = classify_gemini_http_error(429, "Quota exceeded")
        assert status == 429
        assert "quota" in detail.lower()


class TestHttpExceptionFromGeminiError:
    def test_dunning_returns_english_billing_message(self):
        exc = ModelHTTPError(
            status_code=403,
            model_name="gemini-2.5-flash",
            body=DUNNING_BODY,
        )
        http_exc = http_exception_from_gemini_error(exc, context="processing")
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 403
        assert "billing" in http_exc.detail
        assert "status_code:" not in http_exc.detail

    def test_non_gemini_error_uses_generic_message(self):
        http_exc = http_exception_from_gemini_error(
            RuntimeError("unexpected"), context="RAG"
        )
        assert http_exc.status_code == 502
        assert "Error during RAG" in http_exc.detail


class TestRaiseForGeminiResponse:
    def test_success_does_not_raise(self):
        request = httpx.Request("POST", "https://example.com")
        response = httpx.Response(
            200, request=request, json={"embedding": {"values": [1.0]}}
        )
        raise_for_gemini_response(response)

    def test_dunning_response_raises_http_exception(self):
        request = httpx.Request("POST", "https://example.com")
        response = httpx.Response(403, request=request, json=DUNNING_BODY)
        with pytest.raises(HTTPException) as err:
            raise_for_gemini_response(response)
        assert err.value.status_code == 403
        assert "billing" in err.value.detail
