"""Unit tests for Phase 4 structured analysis Pydantic schemas."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.schemas import (
    AudienceProfile,
    BrandInfo,
    CompetitorAnalysis,
    CompetitorProfile,
    CompetitorVerificationStatus,
    ContentType,
    KeywordRecommendations,
    LinkAnalysisResponse,
    LLMAnalysisPayload,
    MetaDescriptionRecommendation,
    PriorityLevel,
    SearchIntent,
    SearchPlatform,
    SEOImprovements,
    SEOIssues,
    SEOTitleRecommendation,
    ServiceRecommendation,
    SourceType,
    SupportingContentRecommendation,
    TargetAudience,
    TargetSearchQuery,
    WebsiteAnalysis,
)


def _build_valid_brand() -> BrandInfo:
    return BrandInfo(
        name="Acme Cloud Analytics",
        category="SaaS Analytics",
        summary="Cloud-based product analytics platform for SaaS growth teams.",
    )


def _build_valid_competitor_analysis() -> CompetitorAnalysis:
    competitors = [
        CompetitorProfile(
            name="Mixpanel",
            category="Product Analytics",
            overview="Event-based product analytics for web and mobile teams.",
            key_strengths=["Mature funnel analytics", "Broad SDK ecosystem"],
            potential_weaknesses=["Pricing can scale steeply with event volume"],
            competitive_comparison="Both target SaaS product teams seeking retention insights.",
            verification_status=CompetitorVerificationStatus.AI_SUGGESTED,
            reason_for_similarity="Offers SaaS funnel and retention cohort analytics.",
        ),
        CompetitorProfile(
            name="Amplitude",
            category="Digital Analytics",
            overview="Digital analytics platform focused on user behavior and experimentation.",
            key_strengths=["Enterprise experimentation workflows"],
            potential_weaknesses=["Steeper onboarding curve for small teams"],
            competitive_comparison="Competes on SaaS product telemetry and cohort analysis.",
            reason_for_similarity="Directly overlaps on product telemetry and growth insights.",
        ),
        CompetitorProfile(
            name="PostHog",
            category="Product Analytics",
            overview="Developer-friendly product analytics and session insights suite.",
            key_strengths=["Self-hosting options", "Integrated feature flags"],
            potential_weaknesses=["Broader suite may add complexity for non-technical users"],
            competitive_comparison="Targets fast-growing SaaS startups with product telemetry.",
            reason_for_similarity="Targets startup and SaaS teams analyzing product funnels.",
        ),
    ]
    return CompetitorAnalysis(
        brand_overview="Acme Cloud Analytics provides funnel, cohort, and customer health analytics.",
        competitors=competitors,
        brand_strengths=["Focused SaaS growth workflows", "Sub-second dashboards"],
        competitive_advantages=["Automated growth insights tailored to SaaS telemetry"],
        market_positioning="Lightweight AI-assisted analytics platform for growing SaaS teams.",
        opportunities=["Publish vertical-specific SaaS case studies"],
    )


def _build_valid_search_queries() -> list[TargetSearchQuery]:
    return [
        TargetSearchQuery(
            query="best SaaS product analytics platform for startups",
            platforms=[SearchPlatform.GOOGLE, SearchPlatform.LINKEDIN],
            intent=SearchIntent.COMMERCIAL,
            business_relevance="Directly matches high-intent SaaS buyers evaluating analytics tools.",
            target_audience="SaaS founders and heads of growth",
        ),
        TargetSearchQuery(
            query="how to track SaaS retention cohorts automatically",
            platforms=[SearchPlatform.GOOGLE, SearchPlatform.X],
            intent=SearchIntent.INFORMATIONAL,
            business_relevance="Connects educational searchers to cohort analytics features.",
            target_audience="Product managers",
        ),
        TargetSearchQuery(
            query="real-time SaaS revenue and funnel dashboard tool",
            platforms=[SearchPlatform.GOOGLE],
            intent=SearchIntent.TRANSACTIONAL,
            business_relevance="Matches buyers ready to adopt a dashboard solution.",
            target_audience="RevOps and analytics leads",
        ),
        TargetSearchQuery(
            query="B2B SaaS customer health monitoring software",
            platforms=[SearchPlatform.LINKEDIN, SearchPlatform.GOOGLE],
            intent=SearchIntent.BUSINESS_DISCOVERY,
            business_relevance="Aligns with customer health scoring capability on the site.",
            target_audience="Customer success leaders",
        ),
        TargetSearchQuery(
            query="SaaS growth analytics dashboard examples",
            platforms=[SearchPlatform.INSTAGRAM, SearchPlatform.FACEBOOK],
            intent=SearchIntent.INSPIRATION,
            business_relevance="Showcases visual dashboard layouts to prospective teams.",
            target_audience="Growth marketers",
        ),
    ]


def _build_valid_seo_improvements() -> SEOImprovements:
    return SEOImprovements(
        keyword_recommendations=KeywordRecommendations(
            primary_keyword="SaaS product analytics platform",
            secondary_keywords=["SaaS retention cohort analytics", "customer health dashboards"],
            long_tail_keywords=["automated product telemetry analytics for SaaS startups"],
            related_keywords=["funnel tracking software", "SaaS growth insights"],
        ),
        recommended_seo_title=SEOTitleRecommendation(
            recommended_title="Acme Cloud Analytics | SaaS Product Analytics Platform",
            primary_keyword="SaaS product analytics platform",
            reason="Pairs brand identity with the primary commercial keyword clearly.",
        ),
        recommended_meta_description=MetaDescriptionRecommendation(
            recommended_meta_description=(
                "Monitor SaaS funnels, retention cohorts, and customer health scores "
                "with Acme Cloud Analytics. Turn product telemetry into growth actions."
            ),
            target_keyword="SaaS funnels",
            explanation="Highlights core features and concrete value without keyword stuffing.",
        ),
        supporting_content=[
            SupportingContentRecommendation(
                content_type=ContentType.SERVICE_PAGE,
                suggested_title="SaaS Retention Cohort Analytics",
                target_keyword="SaaS retention cohort analytics",
                purpose="Capture commercial search intent for cohort tracking.",
                target_audience="Product managers and growth leads",
                priority=PriorityLevel.HIGH,
            ),
            SupportingContentRecommendation(
                content_type=ContentType.CASE_STUDY,
                suggested_title="How a B2B SaaS Team Improved Trial Conversion with Telemetry",
                target_keyword="SaaS funnel analytics case study",
                purpose="Build buyer trust with concrete workflow outcomes.",
                target_audience="SaaS founders",
                priority=PriorityLevel.MEDIUM,
            ),
        ],
        seo_issues=SEOIssues(
            observed_issues=["Homepage lacks dedicated H2 sections for pricing and integrations."],
            recommended_improvements=["Create dedicated landing pages per core analytics module."],
            potential_technical_audit_items=[
                "Verify Core Web Vitals, XML sitemap, and canonical tags via a technical crawl."
            ],
        ),
    )


def _build_valid_services() -> list[ServiceRecommendation]:
    return [
        ServiceRecommendation(
            service_name="Funnel Monitoring",
            description="Tracks multi-step user conversion funnels across SaaS workflows.",
            target_industry=["B2B SaaS"],
            target_customer=["Product teams", "Growth leads"],
            main_benefit="Identifies conversion drop-offs rapidly.",
            source_type=SourceType.WEBSITE_IDENTIFIED,
            evidence="Monitors funnels, retention cohorts, and customer health scores.",
        ),
        ServiceRecommendation(
            service_name="Retention Cohort Analytics",
            description="Segments user cohorts to measure long-term product retention.",
            target_industry=["B2B SaaS", "Subscription Software"],
            target_customer=["Product managers"],
            main_benefit="Reveals drivers of sustained customer retention.",
            source_type=SourceType.WEBSITE_IDENTIFIED,
            evidence="Monitors funnels, retention cohorts, and customer health scores.",
        ),
        ServiceRecommendation(
            service_name="Customer Health Scoring",
            description="Aggregates usage signals to highlight expansion and churn risks.",
            target_industry=["B2B SaaS"],
            target_customer=["Customer success teams"],
            main_benefit="Enables proactive churn prevention.",
            source_type=SourceType.WEBSITE_IDENTIFIED,
            evidence="Monitors funnels, retention cohorts, and customer health scores.",
        ),
        ServiceRecommendation(
            service_name="Real-Time Revenue Dashboards",
            description="Provides sub-second revenue metric dashboards with custom alerts.",
            target_industry=["SaaS", "Technology"],
            target_customer=["Founders", "RevOps teams"],
            main_benefit="Delivers immediate visibility into revenue KPIs.",
            source_type=SourceType.WEBSITE_IDENTIFIED,
            evidence="Track key revenue metrics with sub-second queries and customizable alerts.",
        ),
        ServiceRecommendation(
            service_name="Analytics Implementation Advisory",
            description="Guided instrumentation and telemetry event taxonomy setup.",
            target_industry=["B2B SaaS"],
            target_customer=["Early-stage engineering teams"],
            main_benefit="Accelerates clean analytics onboarding.",
            source_type=SourceType.AI_INFERRED,
            evidence=None,
        ),
    ]


def _build_valid_target_audience() -> TargetAudience:
    return TargetAudience(
        primary_audience=["SaaS product leaders", "Startup growth teams"],
        secondary_audience=["Customer success managers", "RevOps analysts"],
        industries=["B2B SaaS", "Cloud Software"],
        business_types=["Growth-stage SaaS startups", "Mid-market software companies"],
        customer_profiles=[
            AudienceProfile(
                audience_segment="SaaS Growth Leaders",
                business_type="B2B SaaS Startup",
                industry="Cloud Software",
                customer_needs=["Clear funnel visibility", "Actionable retention metrics"],
                challenges=["Fragmented telemetry", "Slow reporting cycles"],
                relevant_services=["Funnel Monitoring", "Retention Cohort Analytics"],
                marketing_recommendation="Publish comparison guides and interactive dashboard demos on LinkedIn and Google.",
                source_type=SourceType.WEBSITE_IDENTIFIED,
            )
        ],
        customer_needs=["Fast product telemetry insights", "Proactive retention monitoring"],
        customer_pain_points=["Manual spreadsheet reporting", "Delayed visibility into churn"],
        potential_interests=["Product-led growth", "SaaS metrics benchmarking"],
        geographical_focus=[],
        recommended_marketing_segments=["B2B SaaS Heads of Product", "Seed-to-Series B SaaS Founders"],
        explicitly_identified_audiences=["Growing SaaS teams"],
        inferred_audiences=["Customer success leaders", "RevOps analysts"],
    )


def _build_valid_analysis() -> WebsiteAnalysis:
    return WebsiteAnalysis(
        competitor_analysis=_build_valid_competitor_analysis(),
        target_search_queries=_build_valid_search_queries(),
        seo_improvements=_build_valid_seo_improvements(),
        top_services=_build_valid_services(),
        target_audience=_build_valid_target_audience(),
    )


# ---------------------------------------------------------------------------
# Valid Model Tests
# ---------------------------------------------------------------------------


class TestValidAnalysisSchemas:
    """Verify valid construction across all Phase 4 analysis models."""

    def test_valid_brand_model(self):
        brand = _build_valid_brand()
        assert brand.name == "Acme Cloud Analytics"
        assert brand.source_type == SourceType.WEBSITE_IDENTIFIED

    def test_valid_competitor_model(self):
        analysis = _build_valid_competitor_analysis()
        assert len(analysis.competitors) == 3
        assert all(
            c.verification_status == CompetitorVerificationStatus.AI_SUGGESTED
            for c in analysis.competitors
        )

    def test_competitor_analysis_supports_sparse_content_with_limitations(self):
        sparse = CompetitorAnalysis(
            brand_overview="Minimal landing page with limited business detail.",
            competitors=[],
            market_positioning="Insufficient content to determine positioning.",
            limitations="Website content was too sparse to reliably suggest competitors.",
        )
        assert sparse.competitors == []
        assert sparse.limitations is not None

    def test_valid_search_query_model_and_platform_deduplication(self):
        query = TargetSearchQuery(
            query="best SaaS analytics tool",
            platforms=[SearchPlatform.GOOGLE, SearchPlatform.GOOGLE, SearchPlatform.LINKEDIN],
            intent=SearchIntent.COMMERCIAL,
            business_relevance="High buyer intent.",
            target_audience="SaaS founders",
        )
        assert query.platforms == [SearchPlatform.GOOGLE, SearchPlatform.LINKEDIN]
        assert query.source_type == SourceType.AI_INFERRED

    def test_valid_seo_model(self):
        seo = _build_valid_seo_improvements()
        assert seo.keyword_recommendations.primary_keyword == "SaaS product analytics platform"
        assert len(seo.supporting_content) == 2
        assert len(seo.seo_issues.observed_issues) == 1
        assert len(seo.seo_issues.potential_technical_audit_items) == 1

    def test_valid_service_models_distinguish_fact_vs_inference(self):
        services = _build_valid_services()
        assert len(services) == 5
        assert services[0].source_type == SourceType.WEBSITE_IDENTIFIED
        assert services[0].evidence is not None
        assert services[4].source_type == SourceType.AI_INFERRED

    def test_valid_audience_model(self):
        audience = _build_valid_target_audience()
        assert audience.geographical_focus == []
        assert audience.explicitly_identified_audiences == ["Growing SaaS teams"]
        assert "RevOps analysts" in audience.inferred_audiences

    def test_valid_complete_response_and_json_serialization(self):
        brand = _build_valid_brand()
        analysis = _build_valid_analysis()
        response = LinkAnalysisResponse(
            success=True,
            website="https://acme.example",
            brand=brand,
            analysis=analysis,
        )

        json_str = response.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["success"] is True
        assert parsed["website"] == "https://acme.example"
        assert set(parsed["analysis"].keys()) == {
            "competitor_analysis",
            "target_search_queries",
            "seo_improvements",
            "top_services",
            "target_audience",
        }
        assert len(parsed["analysis"]["target_search_queries"]) == 5
        assert len(parsed["analysis"]["top_services"]) == 5

        # Round-trip deserialization succeeds cleanly
        restored = LinkAnalysisResponse.model_validate_json(json_str)
        assert restored == response

    def test_llm_analysis_payload_round_trip(self):
        payload = LLMAnalysisPayload(
            brand=_build_valid_brand(),
            analysis=_build_valid_analysis(),
        )
        restored = LLMAnalysisPayload.model_validate_json(payload.model_dump_json())
        assert restored.brand.name == "Acme Cloud Analytics"


# ---------------------------------------------------------------------------
# Validation Error Tests
# ---------------------------------------------------------------------------


class TestInvalidAnalysisSchemas:
    """Verify schema constraints reject malformed or invalid AI outputs."""

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            BrandInfo(name="Acme")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            CompetitorProfile(name="Rival")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            LinkAnalysisResponse(success=True, website="https://example.com")  # type: ignore[call-arg]

    def test_whitespace_only_required_strings_rejected(self):
        with pytest.raises(ValidationError):
            BrandInfo(name="   ", category="SaaS", summary="Valid summary")

    @pytest.mark.parametrize("bad_platform", ["TikTok", "Bing", "YouTube", ""])
    def test_invalid_platform_rejected(self, bad_platform: str):
        with pytest.raises(ValidationError):
            TargetSearchQuery(
                query="SaaS analytics tool",
                platforms=[bad_platform],  # type: ignore[list-item]
                intent=SearchIntent.COMMERCIAL,
                business_relevance="Relevant",
                target_audience="Founders",
            )

    @pytest.mark.parametrize("bad_source", ["verified_fact", "external_research", "manual", ""])
    def test_invalid_source_type_rejected(self, bad_source: str):
        with pytest.raises(ValidationError):
            ServiceRecommendation(
                service_name="Analytics",
                description="Product analytics",
                main_benefit="Faster insights",
                source_type=bad_source,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("bad_priority", ["Urgent", "Critical", "P0", ""])
    def test_invalid_priority_rejected(self, bad_priority: str):
        with pytest.raises(ValidationError):
            SupportingContentRecommendation(
                content_type=ContentType.BLOG_ARTICLE,
                suggested_title="SaaS Guide",
                target_keyword="SaaS metrics",
                purpose="Educate prospects",
                target_audience="Founders",
                priority=bad_priority,  # type: ignore[arg-type]
            )

    def test_incorrect_search_query_count_rejected(self):
        queries = _build_valid_search_queries()

        # Fewer than 5 queries rejected
        with pytest.raises(ValidationError):
            WebsiteAnalysis(
                competitor_analysis=_build_valid_competitor_analysis(),
                target_search_queries=queries[:4],
                seo_improvements=_build_valid_seo_improvements(),
                top_services=_build_valid_services(),
                target_audience=_build_valid_target_audience(),
            )

        # More than 5 queries rejected
        extra_query = TargetSearchQuery(
            query="extra sixth search query",
            platforms=[SearchPlatform.GOOGLE],
            intent=SearchIntent.INFORMATIONAL,
            business_relevance="Extra",
            target_audience="Analysts",
        )
        with pytest.raises(ValidationError):
            WebsiteAnalysis(
                competitor_analysis=_build_valid_competitor_analysis(),
                target_search_queries=[*queries, extra_query],
                seo_improvements=_build_valid_seo_improvements(),
                top_services=_build_valid_services(),
                target_audience=_build_valid_target_audience(),
            )

    def test_duplicate_search_queries_rejected(self):
        queries = _build_valid_search_queries()
        duplicate = TargetSearchQuery(
            query=queries[0].query.upper(),
            platforms=[SearchPlatform.GOOGLE],
            intent=SearchIntent.COMMERCIAL,
            business_relevance="Duplicate",
            target_audience="Founders",
        )
        with pytest.raises(ValidationError, match="Duplicate target search query"):
            WebsiteAnalysis(
                competitor_analysis=_build_valid_competitor_analysis(),
                target_search_queries=[*queries[:4], duplicate],
                seo_improvements=_build_valid_seo_improvements(),
                top_services=_build_valid_services(),
                target_audience=_build_valid_target_audience(),
            )

    def test_zero_or_excessive_services_rejected(self):
        services = _build_valid_services()

        with pytest.raises(ValidationError):
            WebsiteAnalysis(
                competitor_analysis=_build_valid_competitor_analysis(),
                target_search_queries=_build_valid_search_queries(),
                seo_improvements=_build_valid_seo_improvements(),
                top_services=[],
                target_audience=_build_valid_target_audience(),
            )

        extra_service = ServiceRecommendation(
            service_name="Sixth Service",
            description="Too many services",
            main_benefit="Exceeds five",
            source_type=SourceType.AI_INFERRED,
        )
        with pytest.raises(ValidationError):
            WebsiteAnalysis(
                competitor_analysis=_build_valid_competitor_analysis(),
                target_search_queries=_build_valid_search_queries(),
                seo_improvements=_build_valid_seo_improvements(),
                top_services=[*services, extra_service],
                target_audience=_build_valid_target_audience(),
            )

