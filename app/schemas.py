"""Pydantic request and response schemas for the API."""

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_url


class RootResponse(BaseModel):
    """Response model for the root endpoint."""

    message: str
    version: str
    status: str


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str


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
