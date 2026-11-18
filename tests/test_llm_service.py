"""Offline unit tests for Phase 5 Gemini LLM service integration.

All Gemini SDK calls are deterministically mocked; no real API key or external
network access is required.
"""

from __future__ import annotations

import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from google.genai import errors as genai_errors
from google.genai import types as genai_types
import httpx
import pytest

from app.prompts.analysis_prompt import SYSTEM_INSTRUCTION
from app.schemas import LLMAnalysisPayload, WebsiteExtractedData
from app.services.llm_service import (
    GeminiLLMService,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMIncompleteResponseError,
    LLMInvalidJSONError,
    LLMInvalidRequestError,
    LLMMaxRetriesExceededError,
    LLMNetworkError,
    LLMPermissionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMSchemaValidationError,
    LLMTimeoutError,
)


def _run(coro):
    """Execute an async coroutine synchronously in pytest."""
    return asyncio.run(coro)


def _sample_website_data() -> WebsiteExtractedData:
    return WebsiteExtractedData(
        requested_url="https://acme.example/start?token=super-secret-query-token",
        final_url="https://acme.example/home?session=private-session-id",
        status_code=200,
        content_type="text/html",
        title="Acme Cloud Analytics",
        meta_description="AI-powered cloud analytics for SaaS teams.",
        meta_keywords=["SaaS analytics", "funnel tracking"],
        h1_headings=["Smarter Analytics for Growing SaaS Teams"],
        h2_headings=["Core Capabilities"],
        h3_headings=["Real-Time Dashboards"],
        main_text="UNIQUE_WEBSITE_BODY_SENTINEL Acme Cloud Analytics monitors SaaS funnels and retention cohorts.",
        content_length=95,
    )


def _valid_llm_payload_dict() -> dict:
    return {
        "brand": {
            "name": "Acme Cloud Analytics",
            "category": "SaaS Product Analytics",
            "summary": "Cloud analytics platform for SaaS funnel and cohort insights.",
            "source_type": "website_identified",
        },
        "analysis": {
            "competitor_analysis": {
                "brand_overview": "Provides SaaS funnel and retention cohort analytics.",
                "competitors": [
                    {
                        "name": "Mixpanel",
                        "category": "Product Analytics",
                        "overview": "Event-based product analytics platform.",
                        "key_strengths": ["Mature funnel reporting"],
                        "potential_weaknesses": ["Costs may scale quickly at high volume"],
                        "competitive_comparison": "Targets similar SaaS product analytics buyers.",
                        "verification_status": "ai_suggested",
                        "reason_for_similarity": "Overlaps on funnel and cohort tracking.",
                    },
                    {
                        "name": "Amplitude",
                        "category": "Digital Analytics",
                        "overview": "Behavioral analytics and experimentation suite.",
                        "key_strengths": ["Enterprise analytics tooling"],
                        "potential_weaknesses": ["Heavier onboarding for small teams"],
                        "competitive_comparison": "Competes for SaaS growth and product teams.",
                        "verification_status": "ai_suggested",
                        "reason_for_similarity": "Direct overlap in product telemetry analytics.",
                    },
                    {
                        "name": "PostHog",
                        "category": "Product Analytics",
                        "overview": "Developer-focused product analytics platform.",
                        "key_strengths": ["Broad developer tooling"],
                        "potential_weaknesses": ["May feel complex for non-technical marketers"],
                        "competitive_comparison": "Targets fast-growing SaaS startups.",
                        "verification_status": "ai_suggested",
                        "reason_for_similarity": "Focuses on SaaS startup product funnels.",
                    },
                ],
                "brand_strengths": ["Focused SaaS analytics workflows"],
                "competitive_advantages": ["Simplified cohort monitoring"],
                "market_positioning": "Focused SaaS funnel and cohort analytics solution.",
                "opportunities": ["Publish SaaS retention benchmarks"],
                "limitations": None,
            },
            "target_search_queries": [
                {
                    "query": "best SaaS product analytics platform for startups",
                    "platforms": ["Google", "LinkedIn"],
                    "intent": "Commercial",
                    "business_relevance": "Captures high-intent SaaS tool buyers.",
                    "target_audience": "SaaS founders",
                    "source_type": "ai_inferred",
                },
                {
                    "query": "how to analyze SaaS retention cohorts",
                    "platforms": ["Google", "X"],
                    "intent": "Informational",
                    "business_relevance": "Aligns with retention cohort capabilities.",
                    "target_audience": "Product managers",
                    "source_type": "ai_inferred",
                },
                {
                    "query": "real-time SaaS funnel dashboard software",
                    "platforms": ["Google"],
                    "intent": "Transactional",
                    "business_relevance": "Matches buyers ready to adopt funnel dashboards.",
                    "target_audience": "Growth leads",
                    "source_type": "ai_inferred",
                },
                {
                    "query": "B2B SaaS cloud analytics vendor",
                    "platforms": ["LinkedIn", "Google"],
                    "intent": "Business Discovery",
                    "business_relevance": "Supports vendor discovery on B2B networks.",
                    "target_audience": "VP of Product",
                    "source_type": "ai_inferred",
                },
                {
                    "query": "SaaS retention dashboard layout inspiration",
                    "platforms": ["Instagram", "Facebook"],
                    "intent": "Inspiration",
                    "business_relevance": "Highlights dashboard visuals for growth teams.",
                    "target_audience": "Growth marketers",
                    "source_type": "ai_inferred",
                },
            ],
            "seo_improvements": {
                "keyword_recommendations": {
                    "primary_keyword": "SaaS product analytics",
                    "secondary_keywords": ["SaaS retention cohort analytics"],
                    "long_tail_keywords": ["real-time funnel analytics for SaaS teams"],
                    "related_keywords": ["product telemetry dashboards"],
                },
                "recommended_seo_title": {
                    "recommended_title": "Acme Cloud Analytics | SaaS Product & Cohort Analytics",
                    "primary_keyword": "SaaS product analytics",
                    "reason": "Clarifies product focus alongside the brand name.",
                },
                "recommended_meta_description": {
                    "recommended_meta_description": (
                        "Monitor SaaS funnels and retention cohorts in real time with "
                        "Acme Cloud Analytics."
                    ),
                    "target_keyword": "SaaS funnels",
                    "explanation": "Concise, value-driven summary without keyword stuffing.",
                },
                "supporting_content": [
                    {
                        "content_type": "Service page",
                        "suggested_title": "SaaS Retention Cohort Analytics",
                        "target_keyword": "SaaS retention cohort analytics",
                        "purpose": "Capture commercial searches for cohort reporting.",
                        "target_audience": "SaaS product managers",
                        "priority": "High",
                    }
                ],
                "seo_issues": {
                    "observed_issues": ["Limited detail on pricing and integrations in main text."],
                    "recommended_improvements": ["Add dedicated feature pages per analytics module."],
                    "potential_technical_audit_items": ["Verify XML sitemap and canonical tags."],
                },
            },
            "top_services": [
                {
                    "service_name": "SaaS Funnel Monitoring",
                    "description": "Tracks user conversion stages across SaaS workflows.",
                    "target_industry": ["B2B SaaS"],
                    "target_customer": ["Product teams"],
                    "main_benefit": "Pinpoints funnel drop-offs quickly.",
                    "source_type": "website_identified",
                    "evidence": "Acme Cloud Analytics monitors SaaS funnels and retention cohorts.",
                },
                {
                    "service_name": "Retention Cohort Analysis",
                    "description": "Evaluates customer retention across signup cohorts.",
                    "target_industry": ["B2B SaaS"],
                    "target_customer": ["Growth teams"],
                    "main_benefit": "Improves long-term subscription retention.",
                    "source_type": "website_identified",
                    "evidence": "Acme Cloud Analytics monitors SaaS funnels and retention cohorts.",
                },
                {
                    "service_name": "Real-Time Dashboards",
                    "description": "Live product telemetry dashboards for SaaS metrics.",
                    "target_industry": ["Cloud Software"],
                    "target_customer": ["Founders"],
                    "main_benefit": "Provides immediate KPI visibility.",
                    "source_type": "website_identified",
                    "evidence": "Real-Time Dashboards",
                },
                {
                    "service_name": "Telemetry Instrumentation Setup",
                    "description": "Event taxonomy and analytics implementation support.",
                    "target_industry": ["B2B SaaS"],
                    "target_customer": ["Engineering teams"],
                    "main_benefit": "Accelerates clean data collection.",
                    "source_type": "ai_inferred",
                    "evidence": None,
                },
                {
                    "service_name": "Growth Reporting Advisory",
                    "description": "KPI dashboard structuring for SaaS leadership.",
                    "target_industry": ["B2B SaaS"],
                    "target_customer": ["RevOps teams"],
                    "main_benefit": "Aligns teams on retention KPIs.",
                    "source_type": "ai_inferred",
                    "evidence": None,
                },
            ],
            "target_audience": {
                "primary_audience": ["Growing SaaS teams", "Product managers"],
                "secondary_audience": ["RevOps analysts"],
                "industries": ["B2B SaaS"],
                "business_types": ["SaaS startups"],
                "customer_profiles": [
                    {
                        "audience_segment": "SaaS Growth Teams",
                        "business_type": "B2B SaaS Startup",
                        "industry": "Cloud Software",
                        "customer_needs": ["Funnel clarity", "Retention insights"],
                        "challenges": ["Slow manual reporting"],
                        "relevant_services": ["SaaS Funnel Monitoring", "Retention Cohort Analysis"],
                        "marketing_recommendation": "Share practical cohort guides on LinkedIn.",
                        "source_type": "website_identified",
                    }
                ],
                "customer_needs": ["Actionable SaaS funnel visibility"],
                "customer_pain_points": ["Fragmented retention tracking"],
                "potential_interests": ["Product-led growth"],
                "geographical_focus": [],
                "recommended_marketing_segments": ["B2B SaaS Product Leaders"],
                "explicitly_identified_audiences": ["Growing SaaS teams"],
                "inferred_audiences": ["RevOps analysts"],
            },
        },
    }


def _make_mock_response(
    *,
    text: str | None = None,
    parsed=None,
    finish_reason: str | None = "STOP",
    block_reason: str | None = None,
    usage_metadata: dict | None = None,
):
    """Build a deterministic fake GenerateContentResponse-like object."""
    candidates = []
    if finish_reason is not None:
        candidates.append(SimpleNamespace(finish_reason=finish_reason))
    prompt_feedback = (
        SimpleNamespace(block_reason=block_reason) if block_reason is not None else None
    )
    usage = SimpleNamespace(**usage_metadata) if usage_metadata is not None else None
    return SimpleNamespace(
        text=text,
        parsed=parsed,
        candidates=candidates,
        prompt_feedback=prompt_feedback,
        usage_metadata=usage,
    )


def _make_mock_client(generate_content_mock: AsyncMock):
    """Build a fake google-genai Client exposing client.aio.models.generate_content."""
    return SimpleNamespace(
        aio=SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content_mock),
            aclose=AsyncMock(),
        )
    )


def _make_api_error(
    code: int,
    status: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> genai_errors.APIError:
    """Create a realistic google-genai ClientError/ServerError with optional headers."""
    fake_response = SimpleNamespace(headers=headers or {}) if headers else None
    payload = {"error": {"code": code, "status": status, "message": message}}
    if 400 <= code < 500:
        return genai_errors.ClientError(code, payload, fake_response)
    if 500 <= code < 600:
        return genai_errors.ServerError(code, payload, fake_response)
    return genai_errors.APIError(code, payload, fake_response)


# ---------------------------------------------------------------------------
# 1. Success, Structured Output Config, Prompt Builder & Dependency Injection
# ---------------------------------------------------------------------------


class TestGeminiLLMServiceSuccess:
    """Verify successful structured analysis, SDK config, and dependency injection."""

    def test_successful_valid_structured_response_returns_llm_analysis_payload(
        self, caplog
    ):
        payload_json = json.dumps(_valid_llm_payload_dict())
        mock_generate = AsyncMock(
            return_value=_make_mock_response(
                text=payload_json,
                usage_metadata={
                    "prompt_token_count": 420,
                    "candidates_token_count": 610,
                    "total_token_count": 1030,
                },
            )
        )
        client = _make_mock_client(mock_generate)
        service = GeminiLLMService(
            api_key="dummy-test-key",
            model="gemini-3.5-flash-lite",
            max_output_tokens=4096,
            client=client,
        )

        with caplog.at_level(logging.INFO, logger="app.services.llm_service"):
            result = _run(service.analyze_website(_sample_website_data()))

        assert isinstance(result, LLMAnalysisPayload)
        assert result.brand.name == "Acme Cloud Analytics"
        assert len(result.analysis.target_search_queries) == 5
        assert len(result.analysis.top_services) == 5
        assert "total_token_count" in caplog.text

    def test_structured_output_config_uses_supported_sdk_properties_and_no_tools(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        )
        client = _make_mock_client(mock_generate)
        service = GeminiLLMService(
            api_key="dummy-test-key",
            model="gemini-3.5-flash-lite",
            max_output_tokens=2048,
            client=client,
        )

        _run(service.analyze_website(_sample_website_data()))

        mock_generate.assert_awaited_once()
        call_kwargs = mock_generate.await_args.kwargs
        assert call_kwargs["model"] == "gemini-3.5-flash-lite"
        config = call_kwargs["config"]
        assert isinstance(config, genai_types.GenerateContentConfig)
        assert config.response_mime_type == "application/json"
        assert config.response_schema is LLMAnalysisPayload
        assert config.system_instruction == SYSTEM_INSTRUCTION
        assert config.max_output_tokens == 2048
        assert config.tools is None

    def test_prompt_builder_is_invoked_with_website_data(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        )
        client = _make_mock_client(mock_generate)
        service = GeminiLLMService(api_key="dummy-test-key", client=client)
        website_data = _sample_website_data()

        with patch(
            "app.services.llm_service.build_analysis_prompt",
            return_value="BUILT_PROMPT_CONTENT",
        ) as mock_builder:
            _run(service.analyze_website(website_data))

        mock_builder.assert_called_once_with(website_data)
        assert mock_generate.await_args.kwargs["contents"] == "BUILT_PROMPT_CONTENT"

    def test_injected_client_is_not_closed_by_service(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        )
        client = _make_mock_client(mock_generate)
        service = GeminiLLMService(api_key="dummy-test-key", client=client)

        result = _run(service.analyze_website(_sample_website_data()))
        assert isinstance(result, LLMAnalysisPayload)
        # Injected client must NOT be closed by the service
        client.aio.aclose.assert_not_awaited()

    def test_parsed_attribute_fallback_still_validates_with_pydantic(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(
                text=None,
                parsed=_valid_llm_payload_dict(),
            )
        )
        service = GeminiLLMService(
            api_key="dummy-test-key", client=_make_mock_client(mock_generate)
        )

        result = _run(service.analyze_website(_sample_website_data()))
        assert isinstance(result, LLMAnalysisPayload)


# ---------------------------------------------------------------------------
# 2. Configuration & Response Validation Failures
# ---------------------------------------------------------------------------


class TestConfigurationAndResponseValidation:
    """Verify missing API key, empty/blocked/truncated outputs, invalid JSON, and schema errors."""

    def test_missing_api_key_raises_configuration_error(self):
        mock_generate = AsyncMock()
        service = GeminiLLMService(
            api_key="",
            model="gemini-3.5-flash-lite",
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
            _run(service.analyze_website(_sample_website_data()))
        mock_generate.assert_not_awaited()

    def test_missing_model_raises_configuration_error(self):
        service = GeminiLLMService(api_key="dummy-test-key", model="")
        with pytest.raises(LLMConfigurationError, match="GEMINI_MODEL"):
            _run(service.analyze_website(_sample_website_data()))

    @pytest.mark.parametrize(
        "response_obj",
        [
            None,
            _make_mock_response(text="", parsed=None),
            _make_mock_response(text="   \n  ", parsed=None),
        ],
    )
    def test_empty_response_raises_empty_response_error(self, response_obj):
        mock_generate = AsyncMock(return_value=response_obj)
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMEmptyResponseError):
            _run(service.analyze_website(_sample_website_data()))
        # Non-retryable: only called once
        assert mock_generate.await_count == 1

    def test_invalid_json_raises_invalid_json_error_without_retry(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text="{not valid json")
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMInvalidJSONError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    def test_invalid_pydantic_structure_raises_schema_validation_error(self):
        bad_payload = _valid_llm_payload_dict()
        # Only 2 search queries instead of required 5
        bad_payload["analysis"]["target_search_queries"] = bad_payload["analysis"][
            "target_search_queries"
        ][:2]

        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps(bad_payload))
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMSchemaValidationError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    def test_missing_required_fields_raises_schema_validation_error(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps({"brand": {"name": "Only Name"}}))
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMSchemaValidationError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    @pytest.mark.parametrize("block_reason", ["SAFETY", "PROHIBITED_CONTENT", "JAILBREAK"])
    def test_prompt_feedback_block_raises_refusal_error(self, block_reason: str):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(
                text=None, finish_reason=None, block_reason=block_reason
            )
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMRefusalError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    @pytest.mark.parametrize("finish_reason", ["SAFETY", "RECITATION", "PROHIBITED_CONTENT"])
    def test_candidate_refusal_finish_reason_raises_refusal_error(
        self, finish_reason: str
    ):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text="", finish_reason=finish_reason)
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMRefusalError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    def test_truncated_max_tokens_response_raises_incomplete_response_error(self):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(
                text='{"brand": {"name": "Partial',
                finish_reason="MAX_TOKENS",
            )
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMIncompleteResponseError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1


# ---------------------------------------------------------------------------
# 3. API Errors, Retries, Backoff, Retry-After, and Timeouts
# ---------------------------------------------------------------------------


class TestErrorClassificationAndRetryPolicy:
    """Verify permanent vs. transient error handling, retries, and timeouts."""

    @pytest.mark.parametrize(
        ("code", "status", "msg", "expected_exc"),
        [
            (401, "UNAUTHENTICATED", "Invalid credentials", LLMAuthenticationError),
            (400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.", LLMAuthenticationError),
            (403, "PERMISSION_DENIED", "Caller does not have permission", LLMPermissionError),
            (404, "NOT_FOUND", "Model not found", LLMPermissionError),
            (400, "INVALID_ARGUMENT", "Invalid schema property", LLMInvalidRequestError),
        ],
    )
    def test_permanent_errors_do_not_retry(
        self, code: int, status: str, msg: str, expected_exc: type[Exception]
    ):
        mock_generate = AsyncMock(side_effect=_make_api_error(code, status, msg))
        sleep_mock = AsyncMock()
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=3,
            client=_make_mock_client(mock_generate),
            sleep_func=sleep_mock,
        )

        with pytest.raises(expected_exc):
            _run(service.analyze_website(_sample_website_data()))

        assert mock_generate.await_count == 1
        sleep_mock.assert_not_awaited()

    def test_rate_limit_without_retries_raises_rate_limit_error(self):
        mock_generate = AsyncMock(
            side_effect=_make_api_error(429, "RESOURCE_EXHAUSTED", "Quota exceeded")
        )
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=0,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMRateLimitError):
            _run(service.analyze_website(_sample_website_data()))
        assert mock_generate.await_count == 1

    def test_retry_succeeds_after_transient_rate_limit_and_respects_retry_after(self):
        rate_limit_exc = _make_api_error(
            429,
            "RESOURCE_EXHAUSTED",
            "Too many requests",
            headers={"Retry-After": "3"},
        )
        ok_response = _make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        mock_generate = AsyncMock(side_effect=[rate_limit_exc, ok_response])
        sleep_mock = AsyncMock()

        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            retry_base_delay=1.0,
            client=_make_mock_client(mock_generate),
            sleep_func=sleep_mock,
        )

        result = _run(service.analyze_website(_sample_website_data()))
        assert isinstance(result, LLMAnalysisPayload)
        assert mock_generate.await_count == 2
        sleep_mock.assert_awaited_once_with(3.0)

    def test_retry_succeeds_after_transient_503_and_network_error(self):
        server_exc = _make_api_error(503, "UNAVAILABLE", "Service unavailable")
        net_exc = httpx.ConnectError("temporary network glitch")
        ok_response = _make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        mock_generate = AsyncMock(side_effect=[server_exc, net_exc, ok_response])
        sleep_mock = AsyncMock()

        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            retry_base_delay=0.5,
            client=_make_mock_client(mock_generate),
            sleep_func=sleep_mock,
        )

        result = _run(service.analyze_website(_sample_website_data()))
        assert isinstance(result, LLMAnalysisPayload)
        assert mock_generate.await_count == 3
        assert sleep_mock.await_count == 2

    def test_max_retries_respected_and_raises_max_retries_exceeded(self):
        mock_generate = AsyncMock(
            side_effect=_make_api_error(500, "INTERNAL", "Internal server error")
        )
        sleep_mock = AsyncMock()
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=2,
            retry_base_delay=0.25,
            client=_make_mock_client(mock_generate),
            sleep_func=sleep_mock,
        )

        with pytest.raises(LLMMaxRetriesExceededError) as exc_info:
            _run(service.analyze_website(_sample_website_data()))

        assert mock_generate.await_count == 3  # 1 initial + 2 retries
        assert sleep_mock.await_count == 2
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_error, LLMProviderError)

    def test_timeout_handling_without_retries_raises_timeout_error(self):
        async def slow_generate(**kwargs):
            await asyncio.sleep(0.2)
            return _make_mock_response(text=json.dumps(_valid_llm_payload_dict()))

        service = GeminiLLMService(
            api_key="dummy-test-key",
            timeout_seconds=0.02,
            max_retries=0,
            client=_make_mock_client(AsyncMock(side_effect=slow_generate)),
        )

        with pytest.raises(LLMTimeoutError):
            _run(service.analyze_website(_sample_website_data()))

    def test_timeout_retries_then_exhausts(self):
        mock_generate = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        sleep_mock = AsyncMock()
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=1,
            client=_make_mock_client(mock_generate),
            sleep_func=sleep_mock,
        )

        with pytest.raises(LLMMaxRetriesExceededError) as exc_info:
            _run(service.analyze_website(_sample_website_data()))

        assert mock_generate.await_count == 2
        assert isinstance(exc_info.value.last_error, LLMTimeoutError)

    def test_network_error_without_retries_raises_network_error(self):
        mock_generate = AsyncMock(side_effect=httpx.ConnectError("DNS failure"))
        service = GeminiLLMService(
            api_key="dummy-test-key",
            max_retries=0,
            client=_make_mock_client(mock_generate),
        )
        with pytest.raises(LLMNetworkError):
            _run(service.analyze_website(_sample_website_data()))


# ---------------------------------------------------------------------------
# 4. Security & Logging Hygiene Tests
# ---------------------------------------------------------------------------


class TestLoggingAndSecurityHygiene:
    """Verify API keys, prompts, website content, and query params never leak."""

    def test_no_api_key_leakage_in_errors_or_logs(self, caplog):
        secret_key = "AIzaSy-SUPER-SECRET-SENTINEL-KEY-987654"
        # Simulate provider echoing sensitive key material in raw APIError message
        mock_generate = AsyncMock(
            side_effect=_make_api_error(
                401,
                "UNAUTHENTICATED",
                f"Rejected api key {secret_key}",
            )
        )
        service = GeminiLLMService(
            api_key=secret_key,
            client=_make_mock_client(mock_generate),
        )

        with caplog.at_level(logging.DEBUG, logger="app.services.llm_service"):
            with pytest.raises(LLMAuthenticationError) as exc_info:
                _run(service.analyze_website(_sample_website_data()))

        assert secret_key not in str(exc_info.value)
        assert exc_info.value.__cause__ is None
        assert secret_key not in caplog.text

    def test_logs_do_not_expose_website_content_prompts_or_query_params(self, caplog):
        mock_generate = AsyncMock(
            return_value=_make_mock_response(text=json.dumps(_valid_llm_payload_dict()))
        )
        service = GeminiLLMService(
            api_key="AIzaSy-ANOTHER-SECRET-KEY",
            client=_make_mock_client(mock_generate),
        )

        with caplog.at_level(logging.DEBUG, logger="app.services.llm_service"):
            _run(service.analyze_website(_sample_website_data()))

        assert "UNIQUE_WEBSITE_BODY_SENTINEL" not in caplog.text
        assert "private-session-id" not in caplog.text
        assert "super-secret-query-token" not in caplog.text
        assert "AIzaSy-ANOTHER-SECRET-KEY" not in caplog.text
        assert "UNTRUSTED_WEBSITE_DATA" not in caplog.text
        assert "gemini-3.5-flash-lite" in caplog.text

