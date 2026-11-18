"""Pydantic request, extraction, and structured analysis schemas for the API."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_url


def _strip_non_empty(value: str) -> str:
    """Strip whitespace and reject empty or whitespace-only strings."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Field cannot be empty or whitespace only.")
    return cleaned


# ---------------------------------------------------------------------------
# Phase 1 — General & Health Schemas
# ---------------------------------------------------------------------------


class RootResponse(BaseModel):
    """Response model for the root endpoint."""

    message: str
    version: str
    status: str


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str


# ---------------------------------------------------------------------------
# Phase 2 — Request Validation Schema
# ---------------------------------------------------------------------------


class LinkAnalysisRequest(BaseModel):
    """Request model for submitting a website URL for analysis."""

    url: str = Field(
        ...,
        description="Publicly accessible HTTP or HTTPS website URL to analyze.",
        examples=["https://example.com"],
    )

    @field_validator("url")
    @classmethod
    def validate_website_url(cls, value: str) -> str:
        """Validate, SSRF-check, and normalize the submitted website URL."""
        return validate_url(value)


# ---------------------------------------------------------------------------
# Phase 3 — Website Extraction Schemas
# ---------------------------------------------------------------------------


class ExtractedLink(BaseModel):
    """A single relevant hyperlink extracted from a webpage."""

    text: str
    url: str
    is_internal: bool


class ExtractedImage(BaseModel):
    """Extracted metadata for a webpage image without downloading image bytes."""

    alt: str
    url: str | None = None


class WebsiteExtractedData(BaseModel):
    """Structured website content extracted for downstream analysis."""

    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    title: str | None = None
    meta_description: str | None = None
    meta_keywords: list[str] = Field(default_factory=list)
    h1_headings: list[str] = Field(default_factory=list)
    h2_headings: list[str] = Field(default_factory=list)
    h3_headings: list[str] = Field(default_factory=list)
    main_text: str = ""
    internal_links: list[ExtractedLink] = Field(default_factory=list)
    external_links: list[ExtractedLink] = Field(default_factory=list)
    image_alt_texts: list[str] = Field(default_factory=list)
    images: list[ExtractedImage] = Field(default_factory=list)
    content_length: int = 0


# ---------------------------------------------------------------------------
# Phase 4 — Shared Enums (Fact vs Inference & Controlled Vocabularies)
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    """Distinguishes facts directly identified on the website from AI inferences."""

    WEBSITE_IDENTIFIED = "website_identified"
    AI_INFERRED = "ai_inferred"


class CompetitorVerificationStatus(str, Enum):
    """Indicates how a competitor entry was sourced."""

    AI_SUGGESTED = "ai_suggested"
    WEBSITE_MENTIONED = "website_mentioned"


class SearchPlatform(str, Enum):
    """Supported search and discovery platforms."""

    GOOGLE = "Google"
    FACEBOOK = "Facebook"
    INSTAGRAM = "Instagram"
    LINKEDIN = "LinkedIn"
    X = "X"


class SearchIntent(str, Enum):
    """Supported search intent categories."""

    INFORMATIONAL = "Informational"
    COMMERCIAL = "Commercial"
    TRANSACTIONAL = "Transactional"
    NAVIGATIONAL = "Navigational"
    BUSINESS_DISCOVERY = "Business Discovery"
    INSPIRATION = "Inspiration"


class ContentType(str, Enum):
    """Supported supporting-content recommendation types."""

    SERVICE_PAGE = "Service page"
    LANDING_PAGE = "Landing page"
    BLOG_ARTICLE = "Blog article"
    FAQ = "FAQ"
    INDUSTRY_PAGE = "Industry page"
    LOCATION_PAGE = "Location page"
    CASE_STUDY = "Case study"


class PriorityLevel(str, Enum):
    """Recommendation priority levels."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# ---------------------------------------------------------------------------
# Phase 4 — Brand Schema
# ---------------------------------------------------------------------------


class BrandInfo(BaseModel):
    """High-level brand identity derived from extracted website content."""

    name: str = Field(
        ...,
        min_length=1,
        description="Brand or company name extracted from website content (or domain fallback).",
    )
    category: str = Field(
        ...,
        min_length=1,
        description="Primary business category reflecting the submitted website.",
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Concise summary of the business grounded in extracted website content.",
    )
    source_type: SourceType = Field(
        default=SourceType.WEBSITE_IDENTIFIED,
        description="Indicates whether brand identity was identified on the website or inferred.",
    )

    @field_validator("name", "category", "summary")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


# ---------------------------------------------------------------------------
# Phase 4 — Section 1: Competitor vs Brand Analysis
# ---------------------------------------------------------------------------


class CompetitorProfile(BaseModel):
    """Individual competitor comparison entry."""

    name: str = Field(
        ...,
        min_length=1,
        description="Meaningful, business-relevant competitor name.",
    )
    category: str = Field(
        ...,
        min_length=1,
        description="Business category of the competitor.",
    )
    overview: str = Field(
        ...,
        min_length=1,
        description="Concise overview of the competitor's offering.",
    )
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Key strengths associated with the competitor.",
    )
    potential_weaknesses: list[str] = Field(
        default_factory=list,
        description="Potential weaknesses framed cautiously rather than as verified facts.",
    )
    competitive_comparison: str = Field(
        ...,
        min_length=1,
        description="How this competitor compares with the submitted brand.",
    )
    verification_status: CompetitorVerificationStatus = Field(
        default=CompetitorVerificationStatus.AI_SUGGESTED,
        description="Marks competitor suggestions as AI-generated rather than independent research.",
    )
    reason_for_similarity: str = Field(
        ...,
        min_length=1,
        description="Clear explanation of why this company is a relevant competitor.",
    )

    @field_validator("name", "category", "overview", "competitive_comparison", "reason_for_similarity")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


class CompetitorAnalysis(BaseModel):
    """Section 1: Competitor vs Brand Analysis."""

    brand_overview: str = Field(
        ...,
        min_length=1,
        description="Overview of the submitted brand grounded in extracted website content.",
    )
    competitors: list[CompetitorProfile] = Field(
        default_factory=list,
        description="Relevant competitors (target at least 3 when sufficient website content exists).",
    )
    brand_strengths: list[str] = Field(
        default_factory=list,
        description="Strengths of the submitted brand supported by website content.",
    )
    competitive_advantages: list[str] = Field(
        default_factory=list,
        description="Differentiators and competitive advantages.",
    )
    market_positioning: str = Field(
        ...,
        min_length=1,
        description="Summary of the brand's market positioning.",
    )
    opportunities: list[str] = Field(
        default_factory=list,
        description="Actionable competitive and positioning opportunities.",
    )
    limitations: str | None = Field(
        default=None,
        description="Explicit note on uncertainty if website content was insufficient to suggest competitors.",
    )

    @field_validator("brand_overview", "market_positioning")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


# ---------------------------------------------------------------------------
# Phase 4 — Section 2: Target Search Queries
# ---------------------------------------------------------------------------


class TargetSearchQuery(BaseModel):
    """Individual recommended search query."""

    query: str = Field(
        ...,
        min_length=1,
        description="Specific, business-relevant search query.",
    )
    platforms: list[SearchPlatform] = Field(
        ...,
        min_length=1,
        description="Recommended platforms for this search query.",
    )
    intent: SearchIntent = Field(
        ...,
        description="Primary search intent category.",
    )
    business_relevance: str = Field(
        ...,
        min_length=1,
        description="Explanation of why this query is relevant to the business.",
    )
    target_audience: str = Field(
        ...,
        min_length=1,
        description="Audience segment likely to perform this search.",
    )
    source_type: SourceType = Field(
        default=SourceType.AI_INFERRED,
        description="Search queries are AI-inferred recommendations.",
    )

    @field_validator("query", "business_relevance", "target_audience")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)

    @field_validator("platforms")
    @classmethod
    def deduplicate_platforms(
        cls, value: list[SearchPlatform]
    ) -> list[SearchPlatform]:
        return list(dict.fromkeys(value))


# ---------------------------------------------------------------------------
# Phase 4 — Section 3: SEO Improvements
# ---------------------------------------------------------------------------


class KeywordRecommendations(BaseModel):
    """Keyword strategy grounded in the website's actual business offerings."""

    primary_keyword: str = Field(
        ...,
        min_length=1,
        description="Primary target keyword aligned with the core business offering.",
    )
    secondary_keywords: list[str] = Field(
        default_factory=list,
        description="Supporting secondary keywords.",
    )
    long_tail_keywords: list[str] = Field(
        default_factory=list,
        description="Specific, lower-ambiguity long-tail keywords.",
    )
    related_keywords: list[str] = Field(
        default_factory=list,
        description="Topically related keywords.",
    )

    @field_validator("primary_keyword")
    @classmethod
    def validate_primary_keyword(cls, value: str) -> str:
        return _strip_non_empty(value)


class SEOTitleRecommendation(BaseModel):
    """Recommended HTML title tag for search visibility."""

    recommended_title: str = Field(
        ...,
        min_length=1,
        description="Concise, search-friendly recommended page title.",
    )
    primary_keyword: str = Field(
        ...,
        min_length=1,
        description="Primary keyword incorporated in the title.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Why this title improves clarity and search relevance.",
    )

    @field_validator("recommended_title", "primary_keyword", "reason")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


class MetaDescriptionRecommendation(BaseModel):
    """Recommended meta description for click-through clarity."""

    recommended_meta_description: str = Field(
        ...,
        min_length=1,
        description="Natural, compelling meta description without keyword stuffing.",
    )
    target_keyword: str = Field(
        ...,
        min_length=1,
        description="Target keyword naturally reflected in the description.",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Explanation of how this improves on the current metadata.",
    )

    @field_validator("recommended_meta_description", "target_keyword", "explanation")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


class SupportingContentRecommendation(BaseModel):
    """Recommended supporting content asset to strengthen SEO coverage."""

    content_type: ContentType = Field(
        ...,
        description="Type of supporting content asset.",
    )
    suggested_title: str = Field(
        ...,
        min_length=1,
        description="Suggested title or topic for the content asset.",
    )
    target_keyword: str = Field(
        ...,
        min_length=1,
        description="Target keyword for this content piece.",
    )
    purpose: str = Field(
        ...,
        min_length=1,
        description="Strategic purpose of this content.",
    )
    target_audience: str = Field(
        ...,
        min_length=1,
        description="Intended reader or buyer segment.",
    )
    priority: PriorityLevel = Field(
        ...,
        description="Implementation priority (High, Medium, or Low).",
    )

    @field_validator("suggested_title", "target_keyword", "purpose", "target_audience")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


class SEOIssues(BaseModel):
    """Separates observed HTML issues from recommendations and unverified audit checks."""

    observed_issues: list[str] = Field(
        default_factory=list,
        description="Issues directly observable from extracted website content (e.g., missing title or H1).",
    )
    recommended_improvements: list[str] = Field(
        default_factory=list,
        description="Practical on-page and content improvements based on extracted content.",
    )
    potential_technical_audit_items: list[str] = Field(
        default_factory=list,
        description="Potential issues requiring an external technical audit (never claimed as verified facts).",
    )


class SEOImprovements(BaseModel):
    """Section 3: Comprehensive SEO Improvement Recommendations."""

    keyword_recommendations: KeywordRecommendations
    recommended_seo_title: SEOTitleRecommendation
    recommended_meta_description: MetaDescriptionRecommendation
    supporting_content: list[SupportingContentRecommendation] = Field(
        default_factory=list,
        description="Recommended supporting content pieces.",
    )
    seo_issues: SEOIssues = Field(
        default_factory=SEOIssues,
        description="Observed issues, practical improvements, and technical audit considerations.",
    )


# ---------------------------------------------------------------------------
# Phase 4 — Section 4: Top Five Services
# ---------------------------------------------------------------------------


class ServiceRecommendation(BaseModel):
    """Individual core or inferred service entry."""

    service_name: str = Field(
        ...,
        min_length=1,
        description="Clear, specific name of the service.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Concise description of what the service delivers.",
    )
    target_industry: list[str] = Field(
        default_factory=list,
        description="Industries that benefit from this service.",
    )
    target_customer: list[str] = Field(
        default_factory=list,
        description="Customer segments targeted by this service.",
    )
    main_benefit: str = Field(
        ...,
        min_length=1,
        description="Primary value or outcome delivered to customers.",
    )
    source_type: SourceType = Field(
        ...,
        description="Distinguishes explicitly website-identified services from AI-inferred suggestions.",
    )
    evidence: str | None = Field(
        default=None,
        description="Supporting website excerpt or context when available.",
    )

    @field_validator("service_name", "description", "main_benefit")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


# ---------------------------------------------------------------------------
# Phase 4 — Section 5: Target Audience Identification
# ---------------------------------------------------------------------------


class AudienceProfile(BaseModel):
    """Detailed customer profile grounded in website services and content."""

    audience_segment: str = Field(
        ...,
        min_length=1,
        description="Clear label for this audience segment.",
    )
    business_type: str = Field(
        ...,
        min_length=1,
        description="Type of buyer or organization (e.g., B2B SaaS startups, SMB agencies).",
    )
    industry: str = Field(
        ...,
        min_length=1,
        description="Primary industry for this audience profile.",
    )
    customer_needs: list[str] = Field(
        default_factory=list,
        description="Key needs and objectives of this segment.",
    )
    challenges: list[str] = Field(
        default_factory=list,
        description="Primary challenges and pain points.",
    )
    relevant_services: list[str] = Field(
        default_factory=list,
        description="Services from this website most relevant to the segment.",
    )
    marketing_recommendation: str = Field(
        ...,
        min_length=1,
        description="Practical marketing recommendation for reaching this segment.",
    )
    source_type: SourceType = Field(
        default=SourceType.AI_INFERRED,
        description="Indicates whether this audience was explicitly stated on the website or AI-inferred.",
    )

    @field_validator("audience_segment", "business_type", "industry", "marketing_recommendation")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        return _strip_non_empty(value)


class TargetAudience(BaseModel):
    """Section 5: Target Audience Identification."""

    primary_audience: list[str] = Field(
        default_factory=list,
        description="Primary target audience segments.",
    )
    secondary_audience: list[str] = Field(
        default_factory=list,
        description="Secondary target audience segments.",
    )
    industries: list[str] = Field(
        default_factory=list,
        description="Relevant target industries.",
    )
    business_types: list[str] = Field(
        default_factory=list,
        description="Relevant business types.",
    )
    customer_profiles: list[AudienceProfile] = Field(
        default_factory=list,
        description="Detailed customer profiles.",
    )
    customer_needs: list[str] = Field(
        default_factory=list,
        description="Core needs shared across target customers.",
    )
    customer_pain_points: list[str] = Field(
        default_factory=list,
        description="Key pain points addressed by the business.",
    )
    potential_interests: list[str] = Field(
        default_factory=list,
        description="Topics and areas of interest for target customers.",
    )
    geographical_focus: list[str] = Field(
        default_factory=list,
        description="Geographic focus ONLY when supported by website content; otherwise empty.",
    )
    recommended_marketing_segments: list[str] = Field(
        default_factory=list,
        description="Actionable marketing segments for targeting.",
    )
    explicitly_identified_audiences: list[str] = Field(
        default_factory=list,
        description="Audiences explicitly mentioned in the website content.",
    )
    inferred_audiences: list[str] = Field(
        default_factory=list,
        description="Audiences reasonably inferred by AI from the website's services and positioning.",
    )


# ---------------------------------------------------------------------------
# Phase 4 — Combined Analysis & Top-Level API Response Schemas
# ---------------------------------------------------------------------------


class WebsiteAnalysis(BaseModel):
    """Container holding all five required website analysis sections."""

    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[TargetSearchQuery] = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Exactly five unique, business-relevant search query recommendations.",
    )
    seo_improvements: SEOImprovements
    top_services: list[ServiceRecommendation] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Prioritized list of up to five services (target five when supported).",
    )
    target_audience: TargetAudience

    @field_validator("target_search_queries")
    @classmethod
    def validate_unique_queries(
        cls, value: list[TargetSearchQuery]
    ) -> list[TargetSearchQuery]:
        seen: set[str] = set()
        for item in value:
            normalized = item.query.strip().lower()
            if normalized in seen:
                raise ValueError(
                    f"Duplicate target search query detected: '{item.query}'."
                )
            seen.add(normalized)
        return value


class LLMAnalysisPayload(BaseModel):
    """Structured output schema intended for direct LLM generation in Phase 5."""

    brand: BrandInfo
    analysis: WebsiteAnalysis


class LinkAnalysisResponse(BaseModel):
    """Top-level structured API response for website link analysis."""

    success: bool = Field(
        default=True,
        description="Indicates whether website analysis completed successfully.",
    )
    website: str = Field(
        ...,
        min_length=1,
        description="Final analyzed website URL.",
    )
    brand: BrandInfo
    analysis: WebsiteAnalysis

    @field_validator("website")
    @classmethod
    def validate_website_not_empty(cls, value: str) -> str:
        return _strip_non_empty(value)
