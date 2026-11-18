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
