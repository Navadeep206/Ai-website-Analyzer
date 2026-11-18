"""Offline integration tests for POST /link-analysis and HTTP error mapping.

All DNS lookups, website extraction, and Gemini LLM calls are mocked via
FastAPI dependency overrides so the suite runs 100% offline without an API key.
"""

from __future__ import annotations

import logging
import socket
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from app.main import app, get_llm_service, get_website_extractor
from app.schemas import LinkAnalysisResponse
from app.services.llm_service import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMIncompleteResponseError,
    LLMInvalidJSONError,
    LLMMaxRetriesExceededError,
    LLMNetworkError,
    LLMPermissionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMSchemaValidationError,
    LLMTimeoutError,
)
from app.services.website_extractor import (
    UnsafeRedirectError,
    UnsupportedContentTypeError,
    WebsiteAccessDeniedError,
    WebsiteFetchError,
    WebsiteTimeoutError,
    WebsiteTooLargeError,
)
from app.utils.validators import URLValidationError
from tests.test_analysis_service import _sample_extracted_data, _sample_llm_payload


def _public_addrinfo(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


@pytest.fixture
def mock_public_dns():
    with patch(
        "app.utils.validators.socket.getaddrinfo",
        side_effect=_public_addrinfo,
    ):
        yield


@pytest.fixture
def api_client():
    """Provide a TestClient and always clear FastAPI dependency overrides after each test."""
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _override_dependencies(
    *,
    extractor: AsyncMock | None = None,
    llm_service: AsyncMock | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    mock_extractor = extractor or AsyncMock(return_value=_sample_extracted_data())
    if llm_service is None:
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(return_value=_sample_llm_payload())
    else:
        mock_llm = llm_service

    app.dependency_overrides[get_website_extractor] = lambda: mock_extractor
    app.dependency_overrides[get_llm_service] = lambda: mock_llm
    return mock_extractor, mock_llm


# ---------------------------------------------------------------------------
# 1. Success Scenarios & Phase 1 Endpoints
# ---------------------------------------------------------------------------


class TestLinkAnalysisSuccess:
    """Verify end-to-end POST /link-analysis success path with mocked services."""

    def test_valid_url_returns_200_and_valid_link_analysis_response(
        self, api_client: TestClient, mock_public_dns
    ):
        extracted = _sample_extracted_data()
        mock_extractor, mock_llm = _override_dependencies(
            extractor=AsyncMock(return_value=extracted)
        )

        resp = api_client.post(
            "/link-analysis", json={"url": "https://acme.example/"}
        )

        assert resp.status_code == 200
        body = resp.json()

        # Validate complete response against LinkAnalysisResponse schema
        validated = LinkAnalysisResponse.model_validate(body)
        assert validated.success is True
        assert validated.website == extracted.final_url
        assert validated.brand.name == "Acme Cloud Analytics"
        assert set(body["analysis"].keys()) == {
            "competitor_analysis",
            "target_search_queries",
            "seo_improvements",
            "top_services",
            "target_audience",
        }
        assert len(validated.analysis.target_search_queries) == 5
        assert len(validated.analysis.top_services) == 5

        mock_extractor.assert_awaited_once_with("https://acme.example/")
        mock_llm.analyze_website.assert_awaited_once_with(extracted)

    def test_root_and_health_endpoints_still_work(self, api_client: TestClient):
        root_resp = api_client.get("/")
        assert root_resp.status_code == 200
        assert root_resp.json()["status"] == "running"

        health_resp = api_client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# 2. Request Validation & Website Failure Scenarios
# ---------------------------------------------------------------------------


class TestWebsiteFailureMapping:
    """Verify request validation and website extraction exceptions map to safe HTTP errors."""

    @pytest.mark.parametrize(
        "payload",
        [
            {"url": ""},
            {"url": "   "},
            {"url": "not-a-url"},
            {"url": "ftp://example.com"},
            {"url": "javascript:alert(1)"},
            {},
        ],
    )
    def test_invalid_url_returns_422_with_consistent_error_format(
        self, api_client: TestClient, payload: dict
    ):
        mock_extractor, mock_llm = _override_dependencies()

        resp = api_client.post("/link-analysis", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert isinstance(body["error"]["message"], str) and body["error"]["message"]
        mock_extractor.assert_not_awaited()
        mock_llm.analyze_website.assert_not_awaited()

    @pytest.mark.parametrize(
        "unsafe_url",
        [
            "http://localhost",
            "http://127.0.0.1",
            "http://192.168.1.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://user:password@example.com",
        ],
    )
    def test_unsafe_url_returns_422_before_extraction(
        self, api_client: TestClient, unsafe_url: str
    ):
        mock_extractor, mock_llm = _override_dependencies()

        resp = api_client.post("/link-analysis", json={"url": unsafe_url})

        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
        mock_extractor.assert_not_awaited()
        mock_llm.analyze_website.assert_not_awaited()

    @pytest.mark.parametrize(
        ("exc", "expected_status", "expected_code"),
        [
            (URLValidationError("DNS rebinding to loopback"), 422, "UNSAFE_URL"),
            (WebsiteFetchError("HTTP 500 from origin", status_code=500), 502, "WEBSITE_FETCH_FAILED"),
            (WebsiteAccessDeniedError("HTTP 403 denied", status_code=403), 502, "WEBSITE_ACCESS_DENIED"),
            (WebsiteTimeoutError("Timed out"), 504, "WEBSITE_TIMEOUT"),
            (UnsupportedContentTypeError("application/pdf"), 422, "UNSUPPORTED_CONTENT_TYPE"),
            (WebsiteTooLargeError("Exceeded max bytes"), 413, "WEBSITE_RESPONSE_TOO_LARGE"),
            (UnsafeRedirectError("Redirect destination failed security validation."), 422, "UNSAFE_REDIRECT"),
            (UnsafeRedirectError("Redirect loop detected while fetching the website."), 502, "WEBSITE_REDIRECT_FAILED"),
            (UnsafeRedirectError("Exceeded maximum number of redirects (5)."), 502, "WEBSITE_REDIRECT_FAILED"),
            (RuntimeError("Unexpected parser crash"), 500, "INTERNAL_SERVER_ERROR"),
        ],
    )
    def test_extractor_failures_map_to_expected_http_status(
        self,
        api_client: TestClient,
        mock_public_dns,
        exc: Exception,
        expected_status: int,
        expected_code: str,
    ):
        mock_extractor = AsyncMock(side_effect=exc)
        _, mock_llm = _override_dependencies(extractor=mock_extractor)

        resp = api_client.post("/link-analysis", json={"url": "https://example.com"})

        assert resp.status_code == expected_status
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == expected_code
        assert isinstance(body["error"]["message"], str) and body["error"]["message"]
        mock_llm.analyze_website.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Gemini / LLM Failure Scenarios
# ---------------------------------------------------------------------------


class TestLLMFailureMapping:
    """Verify all Gemini service exceptions map to appropriate safe HTTP errors."""

    @pytest.mark.parametrize(
        ("exc", "expected_status", "expected_code"),
        [
            (LLMConfigurationError("Missing GEMINI_API_KEY"), 503, "LLM_NOT_CONFIGURED"),
            (LLMAuthenticationError("Invalid credentials"), 503, "LLM_AUTHENTICATION_FAILED"),
            (LLMPermissionError("Model unavailable"), 503, "LLM_MODEL_UNAVAILABLE"),
            (LLMRateLimitError("Quota exceeded"), 503, "LLM_RATE_LIMITED"),
            (LLMProviderError("Gemini 503"), 503, "LLM_SERVICE_UNAVAILABLE"),
            (LLMNetworkError("Connection dropped"), 503, "LLM_SERVICE_UNAVAILABLE"),
            (LLMTimeoutError("Timed out"), 504, "LLM_TIMEOUT"),
            (
                LLMMaxRetriesExceededError(
                    "Retries exhausted",
                    attempts=3,
                    last_error=LLMTimeoutError("Timed out"),
                ),
                504,
                "LLM_TIMEOUT",
            ),
            (
                LLMMaxRetriesExceededError(
                    "Retries exhausted",
                    attempts=3,
                    last_error=LLMRateLimitError("Rate limited"),
                ),
                503,
                "LLM_RATE_LIMITED",
            ),
            (LLMEmptyResponseError("Empty"), 502, "LLM_EMPTY_RESPONSE"),
            (LLMRefusalError("Safety block"), 502, "LLM_REQUEST_REFUSED"),
            (LLMIncompleteResponseError("MAX_TOKENS"), 502, "LLM_INCOMPLETE_RESPONSE"),
            (LLMInvalidJSONError("Malformed JSON"), 502, "LLM_INVALID_JSON"),
            (LLMSchemaValidationError("Schema mismatch"), 502, "LLM_SCHEMA_VALIDATION_FAILED"),
            (RuntimeError("Unexpected LLM crash"), 500, "INTERNAL_SERVER_ERROR"),
        ],
    )
    def test_llm_failures_map_to_expected_http_status(
        self,
        api_client: TestClient,
        mock_public_dns,
        exc: Exception,
        expected_status: int,
        expected_code: str,
    ):
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(side_effect=exc)
        _override_dependencies(llm_service=mock_llm)

        resp = api_client.post("/link-analysis", json={"url": "https://example.com"})

        assert resp.status_code == expected_status
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == expected_code
        assert isinstance(body["error"]["message"], str) and body["error"]["message"]


# ---------------------------------------------------------------------------
# 4. Security & Information Leakage Scenarios
# ---------------------------------------------------------------------------


class TestSecurityAndLeakagePrevention:
    """Verify error responses and logs never leak secrets, stack traces, or page text."""

    def test_error_responses_never_leak_api_keys_stack_traces_or_website_content(
        self, api_client: TestClient, mock_public_dns
    ):
        secret_key = "AIzaSy-DO-NOT-LEAK-THIS-KEY-999"
        leaked_site_text = "CONFIDENTIAL_WEBSITE_BODY_SNIPPET"

        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(
            side_effect=RuntimeError(
                f"Traceback: key={secret_key} content={leaked_site_text}"
            )
        )
        _override_dependencies(llm_service=mock_llm)

        resp = api_client.post("/link-analysis", json={"url": "https://example.com"})

        assert resp.status_code == 500
        raw_text = resp.text
        assert secret_key not in raw_text
        assert leaked_site_text not in raw_text
        assert "Traceback" not in raw_text
        assert resp.json() == {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred while processing the request.",
            },
        }

    def test_logs_do_not_expose_query_parameters_or_website_content(
        self, api_client: TestClient, mock_public_dns, caplog
    ):
        extracted = _sample_extracted_data()
        _override_dependencies(extractor=AsyncMock(return_value=extracted))

        with caplog.at_level(logging.DEBUG):
            resp = api_client.post(
                "/link-analysis",
                json={"url": "https://acme.example/path?api_token=very-secret-qp"},
            )

        assert resp.status_code == 200
        assert "very-secret-qp" not in caplog.text
        assert "private-session-999" not in caplog.text
        assert "SENSITIVE_PAGE_CONTENT_BODY" not in caplog.text

