"""API contract, malformed payload, dependency error, and OpenAPI QA tests."""

from __future__ import annotations

import asyncio
import socket
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import app, get_llm_service, get_website_extractor
from app.services.llm_service import LLMConfigurationError
from tests.test_analysis_service import _sample_extracted_data, _sample_llm_payload


def _public_addrinfo(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


@pytest.fixture
def mock_public_dns():
    with patch(
        "app.utils.validators.socket.getaddrinfo", side_effect=_public_addrinfo
    ):
        yield


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc
    app.dependency_overrides.clear()


class TestAPIContractAndEdgeCases:
    """Verify request edge cases, dependency error safety, concurrency, and OpenAPI docs."""

    def test_extremely_long_url_rejected_with_422(self, client: TestClient):
        long_url = "https://example.com/" + ("a" * 2100)
        resp = client.post("/link-analysis", json={"url": long_url})
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.parametrize(
        "bad_json_body",
        [
            {"url": 12345},
            {"url": ["https://example.com"]},
            {"url": None},
        ],
    )
    def test_wrong_json_types_rejected_with_422(
        self, client: TestClient, bad_json_body: dict
    ):
        resp = client.post("/link-analysis", json=bad_json_body)
        assert resp.status_code == 422
        assert resp.json()["success"] is False
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_json_and_empty_body_rejected_with_422(self, client: TestClient):
        resp_invalid = client.post(
            "/link-analysis",
            content="{malformed json",
            headers={"content-type": "application/json"},
        )
        assert resp_invalid.status_code == 422
        assert resp_invalid.json()["success"] is False
        assert resp_invalid.json()["error"]["code"] == "VALIDATION_ERROR"

        resp_empty = client.post(
            "/link-analysis",
            content="",
            headers={"content-type": "application/json"},
        )
        assert resp_empty.status_code == 422
        assert resp_empty.json()["success"] is False

    def test_extra_unexpected_fields_ignored_safely(
        self, client: TestClient, mock_public_dns
    ):
        mock_extractor = AsyncMock(return_value=_sample_extracted_data())
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(return_value=_sample_llm_payload())
        app.dependency_overrides[get_website_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_llm_service] = lambda: mock_llm

        resp = client.post(
            "/link-analysis",
            json={"url": "https://acme.example/", "unexpected_flag": True},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_dependency_initialization_failure_returns_safe_error_json(
        self, client: TestClient, mock_public_dns
    ):
        def broken_llm_provider():
            raise LLMConfigurationError("Missing GEMINI_API_KEY")

        app.dependency_overrides[get_llm_service] = broken_llm_provider

        resp = client.post("/link-analysis", json={"url": "https://example.com"})
        assert resp.status_code == 503
        assert resp.json() == {
            "success": False,
            "error": {
                "code": "LLM_NOT_CONFIGURED",
                "message": "The AI analysis service is not properly configured.",
            },
        }

    def test_unexpected_dependency_crash_returns_safe_500_json(
        self, client: TestClient, mock_public_dns
    ):
        def crashing_provider():
            raise RuntimeError("SECRET_TOKEN_XYZ internal crash")

        app.dependency_overrides[get_llm_service] = crashing_provider

        resp = client.post("/link-analysis", json={"url": "https://example.com"})
        assert resp.status_code == 500
        assert "SECRET_TOKEN_XYZ" not in resp.text
        assert resp.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_concurrent_mocked_requests_succeed(self, mock_public_dns):
        mock_extractor = AsyncMock(return_value=_sample_extracted_data())
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(return_value=_sample_llm_payload())
        app.dependency_overrides[get_website_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_llm_service] = lambda: mock_llm

        async def fire_requests():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as ac:
                return await asyncio.gather(
                    ac.post("/link-analysis", json={"url": "https://acme.example/"}),
                    ac.post("/link-analysis", json={"url": "https://acme.example/"}),
                    ac.post("/link-analysis", json={"url": "https://acme.example/"}),
                )

        try:
            responses = asyncio.run(fire_requests())
            assert all(r.status_code == 200 for r in responses)
            assert all(r.json()["success"] is True for r in responses)
        finally:
            app.dependency_overrides.clear()

    def test_openapi_documents_link_analysis_schemas_and_error_responses(
        self, client: TestClient
    ):
        schema = client.get("/openapi.json").json()
        post_spec = schema["paths"]["/link-analysis"]["post"]

        assert "requestBody" in post_spec
        for expected_code in ("200", "413", "422", "500", "502", "503", "504"):
            assert expected_code in post_spec["responses"]

        component_schemas = schema["components"]["schemas"]
        for expected_model in (
            "LinkAnalysisRequest",
            "LinkAnalysisResponse",
            "ErrorResponse",
            "RootResponse",
            "HealthResponse",
        ):
            assert expected_model in component_schemas

    def test_cors_allows_configured_frontend_origin_only(self, client: TestClient):
        allowed = client.options(
            "/link-analysis",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert allowed.status_code == 200
        assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert allowed.headers.get("access-control-allow-credentials") is None

        disallowed = client.options(
            "/link-analysis",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert disallowed.headers.get("access-control-allow-origin") is None

