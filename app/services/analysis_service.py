"""Orchestration service connecting website extraction and Gemini LLM analysis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
import time

from app.schemas import LinkAnalysisResponse, WebsiteExtractedData
from app.services.llm_service import GeminiLLMService
from app.services.website_extractor import extract_website
from app.utils.validators import sanitize_url_for_log

logger = logging.getLogger(__name__)

ExtractorCallable = Callable[[str], Awaitable[WebsiteExtractedData]]


class WebsiteAnalysisService:
    """Coordinates WebsiteExtractor -> GeminiLLMService -> LinkAnalysisResponse."""

    def __init__(
        self,
        *,
        extractor: ExtractorCallable | None = None,
        llm_service: GeminiLLMService | None = None,
    ) -> None:
        self._extractor: ExtractorCallable = extractor or extract_website
        self._llm_service: GeminiLLMService = llm_service or GeminiLLMService()

    async def analyze_url(self, url: str) -> LinkAnalysisResponse:
        """Run the full analysis pipeline for a validated website URL.

        Args:
            url: Normalized, validated public HTTP/HTTPS URL.

        Returns:
            Validated :class:`LinkAnalysisResponse` containing ``success``,
            ``website`` (final URL after safe redirects), ``brand``, and ``analysis``.
        """
        started_at = time.monotonic()
        safe_host = sanitize_url_for_log(url)
        logger.info("Analysis started host=%s", safe_host)

        # 1. Extract and clean website content
        extraction_started = time.monotonic()
        extracted_data = await self._extractor(url)
        extraction_ms = round((time.monotonic() - extraction_started) * 1000, 1)
        safe_final_host = sanitize_url_for_log(extracted_data.final_url)
        logger.info(
            "Extraction completed host=%s duration_ms=%.1f",
            safe_final_host,
            extraction_ms,
        )

        # 2. Run structured Gemini LLM analysis on extracted data
        logger.info("LLM analysis started host=%s", safe_final_host)
        llm_payload = await self._llm_service.analyze_website(extracted_data)

        # 3. Assemble and validate the final API response
        response = LinkAnalysisResponse(
            success=True,
            website=extracted_data.final_url,
            brand=llm_payload.brand,
            analysis=llm_payload.analysis,
        )

        total_ms = round((time.monotonic() - started_at) * 1000, 1)
        logger.info(
            "Analysis completed host=%s total_duration_ms=%.1f",
            safe_final_host,
            total_ms,
        )
        return response

