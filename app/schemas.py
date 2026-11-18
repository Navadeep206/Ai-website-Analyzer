"""Pydantic response schemas for the API."""

from pydantic import BaseModel


class RootResponse(BaseModel):
    """Response model for the root endpoint."""

    message: str
    version: str
    status: str


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str

