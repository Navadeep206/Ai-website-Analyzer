"""Asynchronous Google Gemini LLM service for structured website analysis.

Architecture & Security Notes
-----------------------------
- Uses the official modern Google GenAI Python SDK (``google-genai``) via its
  native asynchronous client interface (``client.aio.models.generate_content``)
  so FastAPI's event loop is never blocked.
- Requests structured JSON matching Phase 4's :class:`LLMAnalysisPayload`
  (``brand`` and ``analysis`` only — never ``success`` or ``website``), and
  re-validates every model output strictly with Pydantic before returning.
- Never enables tools, web browsing, or function execution on Gemini requests.
- Never logs API keys, complete prompts, full website content, sensitive query
  parameters, or raw API response headers/bodies.
- Retries only bounded transient errors (429 rate limits, 5xx provider failures,
  temporary network failures, and timeouts) with exponential backoff, jitter,
  and ``Retry-After`` awareness. Permanent errors (missing/invalid API key,
  permission/model errors, invalid requests, refusals, invalid JSON, and schema
  validation failures) fail fast without retrying.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import random
import time
from typing import Any
from urllib.parse import urlsplit

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.prompts.analysis_prompt import SYSTEM_INSTRUCTION, build_analysis_prompt
from app.schemas import LLMAnalysisPayload, WebsiteExtractedData

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY_SECONDS: float = 30.0
DEFAULT_TEMPERATURE: float = 0.2

# Finish reasons indicating model refusal / policy block
_BLOCKED_FINISH_REASONS: frozenset[str] = frozenset(
    {
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
        "IMAGE_RECITATION",
    }
)

# Finish reasons indicating truncated or abnormal completion
_INCOMPLETE_FINISH_REASONS: frozenset[str] = frozenset(
    {
        "MAX_TOKENS",
        "OTHER",
        "LANGUAGE",
        "MALFORMED_FUNCTION_CALL",
        "UNEXPECTED_TOOL_CALL",
        "NO_IMAGE",
        "IMAGE_OTHER",
    }
)


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy
# ---------------------------------------------------------------------------


class LLMServiceError(Exception):
    """Base exception for Gemini LLM service failures."""


class LLMConfigurationError(LLMServiceError):
    """Raised when Gemini API key or LLM configuration is missing or invalid."""


class LLMAuthenticationError(LLMServiceError):
    """Raised when Gemini rejects the API credentials (HTTP 401 / invalid key)."""


class LLMPermissionError(LLMServiceError):
    """Raised when access is forbidden or the configured model is unavailable."""


class LLMInvalidRequestError(LLMServiceError):
    """Raised when Gemini rejects the request payload or schema (HTTP 400)."""


class LLMRateLimitError(LLMServiceError):
    """Raised when Gemini rate limits or quota limits are exceeded (HTTP 429)."""


class LLMProviderError(LLMServiceError):
    """Raised when Gemini experiences a server-side failure (HTTP 5xx)."""


class LLMNetworkError(LLMServiceError):
    """Raised when a network/transport failure prevents reaching Gemini."""


class LLMTimeoutError(LLMServiceError):
    """Raised when a Gemini request exceeds the configured timeout."""


class LLMResponseError(LLMServiceError):
    """Base exception for empty, blocked, truncated, or invalid model outputs."""


class LLMEmptyResponseError(LLMResponseError):
    """Raised when Gemini returns no response or empty text content."""


class LLMRefusalError(LLMResponseError):
    """Raised when Gemini blocks or refuses the prompt or response."""


class LLMIncompleteResponseError(LLMResponseError):
    """Raised when Gemini output is truncated (e.g. MAX_TOKENS) or incomplete."""


class LLMInvalidJSONError(LLMResponseError):
    """Raised when Gemini output cannot be parsed as valid JSON."""


class LLMSchemaValidationError(LLMResponseError):
    """Raised when parsed JSON fails LLMAnalysisPayload Pydantic validation."""


class LLMMaxRetriesExceededError(LLMServiceError):
    """Raised when all retry attempts for a transient LLM failure are exhausted."""

    def __init__(
        self,
        message: str,
        *,
        attempts: int,
        last_error: LLMServiceError,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


_RETRYABLE_ERRORS: tuple[type[LLMServiceError], ...] = (
    LLMRateLimitError,
    LLMProviderError,
    LLMNetworkError,
    LLMTimeoutError,
)


# ---------------------------------------------------------------------------
# Safe Logging & Header Helpers
# ---------------------------------------------------------------------------


def _extract_safe_host(url: str) -> str:
    """Return only scheme and hostname for logs, omitting paths and query params."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme and parsed.hostname:
            return f"{parsed.scheme}://{parsed.hostname}"
    except ValueError:
        pass
    return "<redacted-url>"


def _enum_name(value: Any) -> str | None:
    """Extract normalized uppercase enum or string name safely."""
    if value is None:
        return None
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name.upper()
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return None


def _parse_retry_after_seconds(exc: BaseException) -> float | None:
    """Extract bounded Retry-After delay in seconds from an APIError response."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    raw_retry_after: str | None = None
    try:
        raw_retry_after = headers.get("retry-after") or headers.get("Retry-After")
    except AttributeError:
        return None

    if not raw_retry_after or not isinstance(raw_retry_after, str):
        return None

    value = raw_retry_after.strip()
    if not value:
        return None

    # Numeric delta-seconds format (e.g., "2" or "1.5")
    try:
        seconds = float(value)
        if seconds >= 0:
            return min(seconds, MAX_RETRY_DELAY_SECONDS)
    except ValueError:
        pass

    # HTTP-date format (RFC 7231)
    try:
        target_dt = parsedate_to_datetime(value)
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)
        delta = (target_dt - datetime.now(timezone.utc)).total_seconds()
        if delta > 0:
            return min(delta, MAX_RETRY_DELAY_SECONDS)
        return 0.0
    except (TypeError, ValueError, OverflowError):
        return None


def _extract_usage_log_fields(response: Any) -> dict[str, int]:
    """Return available integer token counts without fabricating missing values."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return {}

    fields: dict[str, int] = {}
    for attr_name in (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "thoughts_token_count",
    ):
        val = getattr(usage, attr_name, None)
        if isinstance(val, int) and not isinstance(val, bool):
            fields[attr_name] = val
    return fields


def _classify_api_error(exc: genai_errors.APIError) -> LLMServiceError:
    """Map a google-genai APIError into a safe, typed domain exception.

    Never copies raw response bodies, headers, or API keys into caller-facing
    error messages.
    """
    code = getattr(exc, "code", None)
    status = str(getattr(exc, "status", "") or "").upper()
    message_lower = str(getattr(exc, "message", "") or "").lower()

    # Invalid API key (Gemini may return 401 UNAUTHENTICATED or 400 API_KEY_INVALID)
    if (
        code == 401
        or status == "UNAUTHENTICATED"
        or "api key" in message_lower
        or "api_key_invalid" in message_lower
    ):
        return LLMAuthenticationError(
            "Authentication with the Gemini API failed. Please check your API key configuration."
        )

    if code == 403 or status == "PERMISSION_DENIED":
        return LLMPermissionError(
            "Permission denied when accessing the configured Gemini model."
        )

    if code == 404 or status == "NOT_FOUND":
        return LLMPermissionError(
            "The configured Gemini model was not found or is unavailable."
        )

    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return LLMRateLimitError(
            "Gemini API rate limit or quota was exceeded. Please try again later."
        )

    if code in (408, 504) or status == "DEADLINE_EXCEEDED":
        return LLMTimeoutError("The Gemini API request timed out.")

    if code == 400 or status == "INVALID_ARGUMENT":
        return LLMInvalidRequestError(
            "The Gemini API rejected the analysis request due to an invalid request or schema."
        )

    if (isinstance(code, int) and 500 <= code < 600) or status in (
        "INTERNAL",
        "UNAVAILABLE",
    ):
        return LLMProviderError(
            "The Gemini service is temporarily unavailable due to a provider-side error."
        )

    return LLMProviderError(
        "An unexpected error occurred while communicating with the Gemini API."
    )


def _inspect_and_validate_response(response: Any) -> LLMAnalysisPayload:
    """Inspect Gemini response metadata and validate structured output via Pydantic."""
    if response is None:
        raise LLMEmptyResponseError("The Gemini model returned no response.")

    # 1. Check prompt-level blocking / refusal
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = _enum_name(getattr(prompt_feedback, "block_reason", None))
    if block_reason and block_reason != "BLOCKED_REASON_UNSPECIFIED":
        raise LLMRefusalError(
            "The AI model blocked the analysis request due to content safety policies."
        )

    # 2. Inspect candidate finish reason if candidates are present
    candidates = getattr(response, "candidates", None)
    if isinstance(candidates, list) and len(candidates) > 0:
        first_candidate = candidates[0]
        finish_reason = _enum_name(getattr(first_candidate, "finish_reason", None))
        if finish_reason in _BLOCKED_FINISH_REASONS:
            raise LLMRefusalError(
                "The AI model refused or blocked generation of the analysis."
            )
        if finish_reason in _INCOMPLETE_FINISH_REASONS:
            raise LLMIncompleteResponseError(
                "The AI model output was truncated or incomplete before finishing."
            )

    # 3. Extract and strictly validate JSON against LLMAnalysisPayload
    raw_text = getattr(response, "text", None)
    if isinstance(raw_text, str) and raw_text.strip():
        try:
            parsed_json = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMInvalidJSONError(
                "The AI model returned invalid JSON that could not be parsed."
            ) from exc

        if not isinstance(parsed_json, dict):
            raise LLMSchemaValidationError(
                "The AI model output did not match the expected JSON object structure."
            )

        try:
            return LLMAnalysisPayload.model_validate(parsed_json)
        except ValidationError as exc:
            raise LLMSchemaValidationError(
                "The AI model output failed structured schema validation."
            ) from exc

    # Fallback: if SDK exposed a parsed object without raw text, still re-validate it
    parsed_attr = getattr(response, "parsed", None)
    if parsed_attr is not None:
        raw_payload = (
            parsed_attr.model_dump()
            if isinstance(parsed_attr, BaseModel)
            else parsed_attr
        )
        try:
            return LLMAnalysisPayload.model_validate(raw_payload)
        except ValidationError as exc:
            raise LLMSchemaValidationError(
                "The AI model output failed structured schema validation."
            ) from exc

    raise LLMEmptyResponseError("The AI model returned an empty response.")


# ---------------------------------------------------------------------------
# Gemini LLM Service
# ---------------------------------------------------------------------------


class GeminiLLMService:
    """Reusable asynchronous service for analyzing websites with Google Gemini."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_base_delay: float | None = None,
        max_output_tokens: int | None = None,
        client: Any | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._api_key = (
            settings.gemini_api_key if api_key is None else api_key.strip()
        )
        self.model = settings.gemini_model if model is None else model.strip()
        self.timeout_seconds = (
            settings.llm_timeout_seconds
            if timeout_seconds is None
            else float(timeout_seconds)
        )
        self.max_retries = (
            settings.llm_max_retries if max_retries is None else int(max_retries)
        )
        self.retry_base_delay = (
            settings.llm_retry_base_delay
            if retry_base_delay is None
            else float(retry_base_delay)
        )
        self.max_output_tokens = (
            settings.llm_max_output_tokens
            if max_output_tokens is None
            else int(max_output_tokens)
        )
        self._injected_client = client
        self._sleep = sleep_func or asyncio.sleep

    def _validate_configuration(self) -> None:
        """Validate required configuration right before making an LLM request."""
        if not self._api_key:
            raise LLMConfigurationError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in the environment."
            )
        if not self.model:
            raise LLMConfigurationError(
                "Gemini model is not configured. Set GEMINI_MODEL in the environment."
            )
        if self.timeout_seconds <= 0:
            raise LLMConfigurationError(
                "LLM_TIMEOUT_SECONDS must be greater than zero."
            )
        if self.max_retries < 0:
            raise LLMConfigurationError(
                "LLM_MAX_RETRIES must be zero or greater."
            )
        if self.retry_base_delay < 0:
            raise LLMConfigurationError(
                "LLM_RETRY_BASE_DELAY must be zero or greater."
            )
        if self.max_output_tokens <= 0:
            raise LLMConfigurationError(
                "LLM_MAX_OUTPUT_TOKENS must be greater than zero."
            )

    def _build_generation_config(self) -> genai_types.GenerateContentConfig:
        """Build the Gemini structured-output GenerateContentConfig (no tools)."""
        return genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=LLMAnalysisPayload,
            max_output_tokens=self.max_output_tokens,
            temperature=DEFAULT_TEMPERATURE,
        )

    def _create_client(self) -> genai.Client:
        """Create a configured google-genai Client with millisecond HTTP timeout."""
        timeout_ms = max(1, int(self.timeout_seconds * 1000))
        return genai.Client(
            api_key=self._api_key,
            http_options=genai_types.HttpOptions(timeout=timeout_ms),
        )

    def _compute_backoff_delay(
        self,
        retry_index: int,
        retry_after_seconds: float | None = None,
    ) -> float:
        """Compute bounded exponential backoff with jitter, respecting Retry-After."""
        if retry_after_seconds is not None:
            return min(max(0.0, retry_after_seconds), MAX_RETRY_DELAY_SECONDS)
        exponential = self.retry_base_delay * (2**retry_index)
        jitter = random.uniform(0.0, self.retry_base_delay * 0.5)
        return min(exponential + jitter, MAX_RETRY_DELAY_SECONDS)

    async def analyze_website(
        self,
        website_data: WebsiteExtractedData,
    ) -> LLMAnalysisPayload:
        """Analyze extracted website content and return a validated LLMAnalysisPayload.

        Args:
            website_data: Structured content produced by Phase 3 website extraction.

        Returns:
            Validated :class:`LLMAnalysisPayload` containing ``brand`` and ``analysis``.

        Raises:
            LLMServiceError: (or a more specific subclass) on configuration,
                provider, timeout, network, refusal, JSON, schema, or retry errors.
        """
        self._validate_configuration()

        safe_target = _extract_safe_host(website_data.final_url)
        prompt = build_analysis_prompt(website_data)
        config = self._build_generation_config()

        owns_client = self._injected_client is None
        client = self._injected_client if not owns_client else self._create_client()

        started_at = time.monotonic()
        total_attempts = self.max_retries + 1

        logger.info(
            "LLM analysis started model=%s target=%s max_output_tokens=%d",
            self.model,
            safe_target,
            self.max_output_tokens,
        )

        last_transient_error: LLMServiceError | None = None

        try:
            for attempt in range(1, total_attempts + 1):
                retry_after: float | None = None
                try:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=self.model,
                            contents=prompt,
                            config=config,
                        ),
                        timeout=self.timeout_seconds,
                    )
                    validated_payload = _inspect_and_validate_response(response)
                except genai_errors.APIError as exc:
                    classified = _classify_api_error(exc)
                    retry_after = _parse_retry_after_seconds(exc)
                    if not isinstance(classified, _RETRYABLE_ERRORS):
                        duration_ms = round((time.monotonic() - started_at) * 1000, 1)
                        logger.warning(
                            "LLM analysis failed (non-retryable) model=%s category=%s duration_ms=%.1f",
                            self.model,
                            type(classified).__name__,
                            duration_ms,
                        )
                        raise classified from None
                    last_transient_error = classified
                except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException):
                    last_transient_error = LLMTimeoutError(
                        "The Gemini API request timed out."
                    )
                except (httpx.RequestError, OSError, ConnectionError):
                    last_transient_error = LLMNetworkError(
                        "A network error occurred while communicating with the Gemini API."
                    )
                except LLMServiceError as exc:
                    duration_ms = round((time.monotonic() - started_at) * 1000, 1)
                    logger.warning(
                        "LLM analysis failed model=%s category=%s duration_ms=%.1f",
                        self.model,
                        type(exc).__name__,
                        duration_ms,
                    )
                    raise
                else:
                    duration_ms = round((time.monotonic() - started_at) * 1000, 1)
                    usage = _extract_usage_log_fields(response)
                    if usage:
                        logger.info(
                            "LLM analysis succeeded model=%s attempt=%d duration_ms=%.1f usage=%s",
                            self.model,
                            attempt,
                            duration_ms,
                            usage,
                        )
                    else:
                        logger.info(
                            "LLM analysis succeeded model=%s attempt=%d duration_ms=%.1f",
                            self.model,
                            attempt,
                            duration_ms,
                        )
                    return validated_payload

                # Transient failure handling
                if attempt < total_attempts:
                    delay = self._compute_backoff_delay(
                        retry_index=attempt - 1,
                        retry_after_seconds=retry_after,
                    )
                    logger.warning(
                        "LLM transient failure; retrying model=%s attempt=%d/%d category=%s delay_s=%.2f",
                        self.model,
                        attempt,
                        total_attempts,
                        type(last_transient_error).__name__,
                        delay,
                    )
                    await self._sleep(delay)
                    continue

                # Retries exhausted
                duration_ms = round((time.monotonic() - started_at) * 1000, 1)
                logger.error(
                    "LLM analysis failed after attempts=%d model=%s category=%s duration_ms=%.1f",
                    attempt,
                    self.model,
                    type(last_transient_error).__name__,
                    duration_ms,
                )
                if self.max_retries > 0:
                    raise LLMMaxRetriesExceededError(
                        "The Gemini service failed after reaching the maximum number of retry attempts.",
                        attempts=attempt,
                        last_error=last_transient_error,
                    ) from last_transient_error
                raise last_transient_error
        finally:
            if owns_client:
                aio_client = getattr(client, "aio", None)
                aclose = getattr(aio_client, "aclose", None)
                if callable(aclose):
                    try:
                        await aclose()
                    except Exception:
                        pass

        # Unreachable safeguard for static type checkers
        raise LLMProviderError("Unexpected termination of LLM analysis workflow.")


async def analyze_website(
    website_data: WebsiteExtractedData,
    *,
    service: GeminiLLMService | None = None,
) -> LLMAnalysisPayload:
    """Analyze extracted website data with Gemini and return a validated payload.

    Args:
        website_data: Structured content extracted in Phase 3.
        service: Optional preconfigured :class:`GeminiLLMService` instance
            (useful for dependency injection and testing).

    Returns:
        Validated :class:`LLMAnalysisPayload`.
    """
    active_service = service or GeminiLLMService()
    return await active_service.analyze_website(website_data)

