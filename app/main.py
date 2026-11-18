"""FastAPI application entry point and HTTP error mapping."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    LinkAnalysisRequest,
    LinkAnalysisResponse,
    RootResponse,
)
from app.services.analysis_service import ExtractorCallable, WebsiteAnalysisService
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
    LLMResponseError,
    LLMSchemaValidationError,
    LLMServiceError,
    LLMTimeoutError,
)
from app.services.website_extractor import (
    UnsafeRedirectError,
    UnsupportedContentTypeError,
    WebsiteAccessDeniedError,
    WebsiteExtractionError,
    WebsiteFetchError,
    WebsiteTimeoutError,
    WebsiteTooLargeError,
    extract_website,
)
from app.utils.validators import URLValidationError

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
)


# ---------------------------------------------------------------------------
# Consistent Error Response Helpers & Exception Mapping
# ---------------------------------------------------------------------------


def _build_error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """Construct a validated, safe JSON error response."""
    payload = ErrorResponse(
        success=False,
        error=ErrorDetail(code=code, message=message),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _map_exception_to_http_error(exc: Exception) -> tuple[int, str, str]:
    """Map domain exceptions to ``(http_status, error_code, safe_message)``.

    More specific subclasses are always checked before their base classes.
    Raw exception details, stack traces, and credentials are never returned.
    """
    # --- URL / SSRF Validation ---
    if isinstance(exc, URLValidationError):
        return (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "UNSAFE_URL",
            "The provided website URL is invalid or points to a restricted destination.",
        )

    # --- Website Extraction (most specific first) ---
    if isinstance(exc, WebsiteTimeoutError):
        return (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "WEBSITE_TIMEOUT",
            "The request to the target website timed out.",
        )
    if isinstance(exc, WebsiteAccessDeniedError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "WEBSITE_ACCESS_DENIED",
            "The target website denied access or rate-limited the request.",
        )
    if isinstance(exc, WebsiteTooLargeError):
        return (
            status.HTTP_413_CONTENT_TOO_LARGE,
            "WEBSITE_RESPONSE_TOO_LARGE",
            "The target website response exceeds the maximum supported size.",
        )
    if isinstance(exc, UnsupportedContentTypeError):
        return (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "UNSUPPORTED_CONTENT_TYPE",
            "The target URL did not return a supported HTML webpage.",
        )
    if isinstance(exc, UnsafeRedirectError):
        msg_lower = str(exc).lower()
        if "loop" in msg_lower or "maximum number of redirects" in msg_lower:
            return (
                status.HTTP_502_BAD_GATEWAY,
                "WEBSITE_REDIRECT_FAILED",
                "The target website redirected too many times or formed a redirect loop.",
            )
        return (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "UNSAFE_REDIRECT",
            "The target website redirected to an invalid or restricted destination.",
        )
    if isinstance(exc, (WebsiteFetchError, WebsiteExtractionError)):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "WEBSITE_FETCH_FAILED",
            "Unable to retrieve or parse content from the provided website.",
        )

    # --- Gemini / LLM Service (most specific first) ---
    if isinstance(exc, LLMMaxRetriesExceededError):
        return _map_exception_to_http_error(exc.last_error)

    if isinstance(exc, LLMConfigurationError):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_NOT_CONFIGURED",
            "The AI analysis service is not properly configured.",
        )
    if isinstance(exc, LLMAuthenticationError):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_AUTHENTICATION_FAILED",
            "The AI analysis service is currently unavailable due to an authentication issue.",
        )
    if isinstance(exc, LLMPermissionError):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_MODEL_UNAVAILABLE",
            "The configured AI analysis model is currently unavailable.",
        )
    if isinstance(exc, LLMRateLimitError):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_RATE_LIMITED",
            "The AI analysis service is temporarily rate-limited. Please try again later.",
        )
    if isinstance(exc, LLMTimeoutError):
        return (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "LLM_TIMEOUT",
            "The AI analysis service timed out while analyzing the website.",
        )
    if isinstance(exc, (LLMProviderError, LLMNetworkError)):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_SERVICE_UNAVAILABLE",
            "The AI analysis service is temporarily unavailable. Please try again later.",
        )
    if isinstance(exc, LLMEmptyResponseError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_EMPTY_RESPONSE",
            "The AI analysis service returned an empty response.",
        )
    if isinstance(exc, LLMRefusalError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_REQUEST_REFUSED",
            "The AI analysis service declined to analyze the provided website content.",
        )
    if isinstance(exc, LLMIncompleteResponseError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_INCOMPLETE_RESPONSE",
            "The AI analysis service returned an incomplete analysis.",
        )
    if isinstance(exc, LLMInvalidJSONError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_INVALID_JSON",
            "The AI analysis service returned malformed structured output.",
        )
    if isinstance(exc, LLMSchemaValidationError):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_SCHEMA_VALIDATION_FAILED",
            "The AI analysis service output did not match the expected analysis schema.",
        )
    if isinstance(exc, (LLMInvalidRequestError, LLMResponseError, LLMServiceError)):
        return (
            status.HTTP_502_BAD_GATEWAY,
            "LLM_ANALYSIS_FAILED",
            "The AI analysis service failed to complete the analysis.",
        )

    # --- Fallback Unexpected Errors ---
    return (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "An unexpected internal error occurred while processing the request.",
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a consistent 422 ErrorResponse for FastAPI/Pydantic validation errors."""
    errors = exc.errors()
    safe_message = "Request validation failed. Provide a valid public HTTP or HTTPS URL."
    if errors:
        raw_msg = str(errors[0].get("msg", "")).strip()
        if raw_msg.startswith("Value error, "):
            raw_msg = raw_msg[len("Value error, ") :].strip()
        if raw_msg and len(raw_msg) <= 200:
            safe_message = raw_msg

    logger.warning(
        "Request validation failed path=%s error_count=%d",
        request.url.path,
        len(errors),
    )
    return _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message=safe_message,
    )


# ---------------------------------------------------------------------------
# FastAPI Dependency Providers
# ---------------------------------------------------------------------------


def get_website_extractor() -> ExtractorCallable:
    """Provide the website extraction service callable."""
    return extract_website


def get_llm_service() -> GeminiLLMService:
    """Provide a GeminiLLMService instance (client created lazily on request)."""
    return GeminiLLMService()


def get_analysis_service(
    extractor: ExtractorCallable = Depends(get_website_extractor),
    llm_service: GeminiLLMService = Depends(get_llm_service),
) -> WebsiteAnalysisService:
    """Assemble the WebsiteAnalysisService with injectable dependencies."""
    return WebsiteAnalysisService(extractor=extractor, llm_service=llm_service)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


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


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    responses={
        413: {"model": ErrorResponse, "description": "Website response exceeds size limit"},
        422: {"model": ErrorResponse, "description": "Invalid/unsafe URL or unsupported content"},
        502: {"model": ErrorResponse, "description": "Website fetch or AI output failure"},
        503: {"model": ErrorResponse, "description": "AI service unavailable or misconfigured"},
        504: {"model": ErrorResponse, "description": "Website or AI request timed out"},
        500: {"model": ErrorResponse, "description": "Unexpected internal server error"},
    },
    tags=["Link Analysis"],
)
async def link_analysis(
    payload: LinkAnalysisRequest,
    analysis_service: WebsiteAnalysisService = Depends(get_analysis_service),
) -> LinkAnalysisResponse | JSONResponse:
    """Validate a website URL, extract its content, and generate structured AI insights."""
    try:
        return await analysis_service.analyze_url(payload.url)
    except Exception as exc:
        http_status, error_code, safe_message = _map_exception_to_http_error(exc)
        if http_status >= 500:
            logger.error(
                "Link analysis failed status=%d code=%s error_category=%s",
                http_status,
                error_code,
                type(exc).__name__,
            )
        else:
            logger.warning(
                "Link analysis rejected status=%d code=%s error_category=%s",
                http_status,
                error_code,
                type(exc).__name__,
            )
        return _build_error_response(
            status_code=http_status,
            code=error_code,
            message=safe_message,
        )
