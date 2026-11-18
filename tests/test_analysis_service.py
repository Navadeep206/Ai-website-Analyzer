"""Offline unit tests for WebsiteAnalysisService orchestration."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from app.schemas import (
    LinkAnalysisResponse,
    LLMAnalysisPayload,
    WebsiteExtractedData,
)
from app.services.analysis_service import WebsiteAnalysisService
from app.services.llm_service import LLMTimeoutError
from app.services.website_extractor import WebsiteFetchError


def _run(coro):
    return asyncio.run(coro)


def _sample_extracted_data() -> WebsiteExtractedData:
    return WebsiteExtractedData(
        requested_url="https://acme.example/?token=secret-query-123",
        final_url="https://www.acme.example/home?session=private-session-999",
        status_code=200,
        content_type="text/html",
        title="Acme Cloud Analytics",
        meta_description="Cloud analytics for SaaS teams.",
        h1_headings=["Smarter SaaS Analytics"],
        main_text="SENSITIVE_PAGE_CONTENT_BODY Acme monitors SaaS funnels and cohorts.",
        content_length=67,
    )


def _sample_llm_payload() -> LLMAnalysisPayload:
    return LLMAnalysisPayload.model_validate(
        {
            "brand": {
                "name": "Acme Cloud Analytics",
                "category": "SaaS Product Analytics",
                "summary": "Cloud product analytics platform for SaaS teams.",
                "source_type": "website_identified",
            },
            "analysis": {
                "competitor_analysis": {
                    "brand_overview": "Provides SaaS funnel and cohort analytics.",
                    "competitors": [
                        {
                            "name": "Mixpanel",
                            "category": "Product Analytics",
                            "overview": "Event-based product analytics.",
                            "key_strengths": ["Funnel reporting"],
                            "potential_weaknesses": ["High event volume pricing"],
                            "competitive_comparison": "Similar SaaS buyer focus.",
                            "verification_status": "ai_suggested",
                            "reason_for_similarity": "Overlaps on funnel analytics.",
                        },
                        {
                            "name": "Amplitude",
                            "category": "Digital Analytics",
                            "overview": "Behavioral product analytics suite.",
                            "key_strengths": ["Experimentation workflows"],
                            "potential_weaknesses": ["Complex setup for small teams"],
                            "competitive_comparison": "Competes for SaaS product teams.",
                            "verification_status": "ai_suggested",
                            "reason_for_similarity": "Targets SaaS cohort telemetry.",
                        },
                        {
                            "name": "PostHog",
                            "category": "Product Analytics",
                            "overview": "Developer-focused product analytics.",
                            "key_strengths": ["Integrated developer tooling"],
                            "potential_weaknesses": ["Broader suite complexity"],
                            "competitive_comparison": "Targets fast-growing startups.",
                            "verification_status": "ai_suggested",
                            "reason_for_similarity": "Focuses on startup funnels.",
                        },
                    ],
                    "brand_strengths": ["Focused SaaS workflows"],
                    "competitive_advantages": ["Fast cohort analysis"],
                    "market_positioning": "Lightweight SaaS funnel analytics tool.",
                    "opportunities": ["Publish SaaS retention benchmarks"],
                    "limitations": None,
                },
                "target_search_queries": [
                    {
                        "query": "best SaaS product analytics platform",
                        "platforms": ["Google", "LinkedIn"],
                        "intent": "Commercial",
                        "business_relevance": "Matches SaaS tool buyers.",
                        "target_audience": "SaaS founders",
                        "source_type": "ai_inferred",
                    },
                    {
                        "query": "how to analyze SaaS retention cohorts",
                        "platforms": ["Google", "X"],
                        "intent": "Informational",
                        "business_relevance": "Matches cohort features.",
                        "target_audience": "Product managers",
                        "source_type": "ai_inferred",
                    },
                    {
                        "query": "real-time SaaS funnel dashboard software",
                        "platforms": ["Google"],
                        "intent": "Transactional",
                        "business_relevance": "Matches buyers ready to adopt.",
                        "target_audience": "Growth leads",
                        "source_type": "ai_inferred",
                    },
                    {
                        "query": "B2B SaaS analytics vendor",
                        "platforms": ["LinkedIn"],
                        "intent": "Business Discovery",
                        "business_relevance": "Supports vendor discovery.",
                        "target_audience": "VP of Product",
                        "source_type": "ai_inferred",
                    },
                    {
                        "query": "SaaS analytics dashboard design examples",
                        "platforms": ["Instagram", "Facebook"],
                        "intent": "Inspiration",
                        "business_relevance": "Showcases dashboard visuals.",
                        "target_audience": "Growth marketers",
                        "source_type": "ai_inferred",
                    },
                ],
                "seo_improvements": {
                    "keyword_recommendations": {
                        "primary_keyword": "SaaS product analytics",
                        "secondary_keywords": ["SaaS cohort analytics"],
                        "long_tail_keywords": ["funnel analytics for SaaS teams"],
                        "related_keywords": ["product telemetry"],
                    },
                    "recommended_seo_title": {
                        "recommended_title": "Acme Cloud Analytics | SaaS Product Analytics",
                        "primary_keyword": "SaaS product analytics",
                        "reason": "Clear brand and primary keyword alignment.",
                    },
                    "recommended_meta_description": {
                        "recommended_meta_description": (
                            "Analyze SaaS funnels and cohorts with Acme Cloud Analytics."
                        ),
                        "target_keyword": "SaaS funnels",
                        "explanation": "Concise, natural value summary.",
                    },
                    "supporting_content": [
                        {
                            "content_type": "Service page",
                            "suggested_title": "SaaS Cohort Analytics",
                            "target_keyword": "SaaS cohort analytics",
                            "purpose": "Capture commercial search intent.",
                            "target_audience": "Product managers",
                            "priority": "High",
                        }
                    ],
                    "seo_issues": {
                        "observed_issues": ["Limited feature detail on homepage."],
                        "recommended_improvements": ["Expand service descriptions."],
                        "potential_technical_audit_items": ["Check sitemap and canonical tags."],
                    },
                },
                "top_services": [
                    {
                        "service_name": "SaaS Funnel Monitoring",
                        "description": "Tracks SaaS conversion funnels.",
                        "target_industry": ["B2B SaaS"],
                        "target_customer": ["Product teams"],
                        "main_benefit": "Identifies funnel drop-offs.",
                        "source_type": "website_identified",
                        "evidence": "Acme monitors SaaS funnels and cohorts.",
                    },
                    {
                        "service_name": "Retention Cohort Analytics",
                        "description": "Tracks customer retention cohorts.",
                        "target_industry": ["B2B SaaS"],
                        "target_customer": ["Growth teams"],
                        "main_benefit": "Improves retention visibility.",
                        "source_type": "website_identified",
                        "evidence": "Acme monitors SaaS funnels and cohorts.",
                    },
                    {
                        "service_name": "Product Telemetry Dashboards",
                        "description": "Live KPI dashboards.",
                        "target_industry": ["B2B SaaS"],
                        "target_customer": ["Founders"],
                        "main_benefit": "Real-time KPI tracking.",
                        "source_type": "ai_inferred",
                        "evidence": None,
                    },
                    {
                        "service_name": "Event Instrumentation Setup",
                        "description": "Analytics tracking plan setup.",
                        "target_industry": ["B2B SaaS"],
                        "target_customer": ["Engineering teams"],
                        "main_benefit": "Clean telemetry collection.",
                        "source_type": "ai_inferred",
                        "evidence": None,
                    },
                    {
                        "service_name": "Growth Metrics Advisory",
                        "description": "SaaS KPI reporting guidance.",
                        "target_industry": ["B2B SaaS"],
                        "target_customer": ["RevOps teams"],
                        "main_benefit": "Aligned leadership metrics.",
                        "source_type": "ai_inferred",
                        "evidence": None,
                    },
                ],
                "target_audience": {
                    "primary_audience": ["SaaS teams", "Product managers"],
                    "secondary_audience": ["RevOps analysts"],
                    "industries": ["B2B SaaS"],
                    "business_types": ["SaaS startups"],
                    "customer_profiles": [
                        {
                            "audience_segment": "SaaS Growth Teams",
                            "business_type": "B2B SaaS Startup",
                            "industry": "Cloud Software",
                            "customer_needs": ["Funnel clarity"],
                            "challenges": ["Slow reporting"],
                            "relevant_services": ["SaaS Funnel Monitoring"],
                            "marketing_recommendation": "Publish cohort guides on LinkedIn.",
                            "source_type": "website_identified",
                        }
                    ],
                    "customer_needs": ["Funnel clarity"],
                    "customer_pain_points": ["Manual reporting"],
                    "potential_interests": ["Product-led growth"],
                    "geographical_focus": [],
                    "recommended_marketing_segments": ["B2B SaaS Product Leaders"],
                    "explicitly_identified_audiences": ["SaaS teams"],
                    "inferred_audiences": ["RevOps analysts"],
                },
            },
        }
    )


class TestWebsiteAnalysisService:
    """Verify orchestration behavior, response assembly, logging, and error propagation."""

    def test_orchestrates_extractor_and_llm_into_link_analysis_response(self, caplog):
        extracted = _sample_extracted_data()
        llm_payload = _sample_llm_payload()

        mock_extractor = AsyncMock(return_value=extracted)
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(return_value=llm_payload)

        service = WebsiteAnalysisService(extractor=mock_extractor, llm_service=mock_llm)

        with caplog.at_level(logging.DEBUG, logger="app.services.analysis_service"):
            result = _run(service.analyze_url("https://acme.example/?token=secret-query-123"))

        assert isinstance(result, LinkAnalysisResponse)
        assert result.success is True
        # Website field uses final_url from extraction data
        assert result.website == extracted.final_url
        assert result.brand == llm_payload.brand
        assert result.analysis == llm_payload.analysis

        mock_extractor.assert_awaited_once_with("https://acme.example/?token=secret-query-123")
        mock_llm.analyze_website.assert_awaited_once_with(extracted)

        # Logs record lifecycle safely without exposing query params or website content
        assert "Analysis started" in caplog.text
        assert "Extraction completed" in caplog.text
        assert "LLM analysis started" in caplog.text
        assert "Analysis completed" in caplog.text
        assert "secret-query-123" not in caplog.text
        assert "private-session-999" not in caplog.text
        assert "SENSITIVE_PAGE_CONTENT_BODY" not in caplog.text

    def test_propagates_extractor_errors_without_calling_llm(self):
        mock_extractor = AsyncMock(side_effect=WebsiteFetchError("Fetch failed", status_code=500))
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock()

        service = WebsiteAnalysisService(extractor=mock_extractor, llm_service=mock_llm)

        with pytest.raises(WebsiteFetchError):
            _run(service.analyze_url("https://acme.example"))

        mock_llm.analyze_website.assert_not_awaited()

    def test_propagates_llm_errors(self):
        mock_extractor = AsyncMock(return_value=_sample_extracted_data())
        mock_llm = AsyncMock()
        mock_llm.analyze_website = AsyncMock(side_effect=LLMTimeoutError("Timed out"))

        service = WebsiteAnalysisService(extractor=mock_extractor, llm_service=mock_llm)

        with pytest.raises(LLMTimeoutError):
            _run(service.analyze_url("https://acme.example"))

