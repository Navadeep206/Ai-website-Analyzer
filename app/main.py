"""FastAPI application entry point."""

from fastapi import FastAPI

from app.config import settings
from app.schemas import HealthResponse, RootResponse

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
)


@app.get("/", response_model=RootResponse, tags=["General"])
async def read_root() -> RootResponse:
    """Return basic API metadata and running status."""
    return RootResponse(
        message=settings.app_name,
        version=settings.app_version,
        status="running",
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Return the service health status."""
    return HealthResponse(status="healthy")

