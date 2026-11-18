"""Reusable, SSRF-safe website fetching, HTML parsing, and content cleaning service.

Architecture & Security Notes
-----------------------------
1. **SSRF & DNS Rebinding Defense**:
   - All URLs (initial and every redirect hop) are validated using Phase 2
     utilities in :mod:`app.utils.validators` (``validate_url``,
     ``validate_redirect_url``, ``validate_ip_address``, ``resolve_hostname_ips``).
   - When using the default transport (:class:`SSRFSafeAsyncTransport`), a custom
     ``httpcore`` network backend (:class:`PinnedSSRFSafeBackend`) resolves DNS
     at TCP connection time, verifies *every* returned IPv4/IPv6 address against
     :func:`validate_ip_address`, and connects directly to a validated IP literal
     via ``anyio.connect_tcp``.
   - Because ``httpcore`` keeps the original hostname on ``request.url.origin``,
     both the HTTP ``Host`` header and TLS SNI / certificate hostname verification
     (``verify=True``) remain intact while preventing a second unvalidated DNS
     lookup between validation and socket creation.
   - ``trust_env=False`` is enforced on ``httpx.AsyncClient`` so environment proxy
     variables (e.g. ``HTTP_PROXY``) cannot bypass SSRF checks.
   - **Remaining Risk**: Connection-level IP pinning eliminates the standard
     Python-level DNS rebinding TOCTOU window, but does not replace network-level
     egress firewalling (e.g., against transparent proxies, cloud-level routing
     anomalies, or custom transports injected by callers).

2. **Redirect Handling**:
   - ``follow_redirects=False`` is strictly enforced on ``httpx.AsyncClient``.
   - Every 3xx redirect is processed manually up to ``MAX_REDIRECTS`` (5), with
     loop detection, ``Location`` validation, and full SSRF + DNS re-validation
     via :func:`validate_redirect_url`.

3. **Response Size & Timeout Protection**:
   - Granular ``httpx.Timeout`` (connect, read, write, pool) plus an overall
     ``anyio.fail_after`` deadline derived from ``settings.request_timeout``.
   - ``Content-Length`` is checked upfront when present, and streamed bytes are
     strictly capped at ``max_response_bytes`` (``settings.max_response_bytes``)
     so missing or lying ``Content-Length`` headers cannot exhaust memory.
   - Cleaned extracted text is capped at ``max_content_length``
     (``settings.max_content_length``) for downstream LLM safety.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import ssl
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import anyio
import httpcore
import httpx
from bs4 import BeautifulSoup, Tag

from app.config import settings
from app.schemas import ExtractedImage, ExtractedLink, WebsiteExtractedData
from app.utils.validators import (
    MAX_REDIRECTS,
    URLValidationError,
    resolve_hostname_ips,
    validate_ip_address,
    validate_redirect_url,
    validate_url,
)

logger = logging.getLogger(__name__)

REDIRECT_STATUS_CODES: frozenset[int] = frozenset({301, 302, 303, 307, 308})
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"text/html", "application/xhtml+xml"}
)

MAX_HEADINGS_PER_LEVEL: int = 50
MAX_INTERNAL_LINKS: int = 50
MAX_EXTERNAL_LINKS: int = 30
MAX_IMAGES: int = 30

# Tags that never carry primary readable article/business text
ALWAYS_REMOVE_TAGS: tuple[str, ...] = (
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "nav",
    "footer",
    "form",
    "button",
    "template",
    "object",
    "embed",
)

# Short UI boilerplate lines that add noise without semantic value
_BOILERPLATE_LINES: frozenset[str] = frozenset(
    {
        "skip to content",
        "skip to main content",
        "skip navigation",
        "toggle navigation",
        "open menu",
        "close menu",
        "menu",
        "back to top",
        "accept all cookies",
        "accept cookies",
        "manage cookies",
        "cookie settings",
        "privacy choices",
    }
)

_WHITESPACE_RE = re.compile(r"[ \t\r\f\v\u00a0\u200b]+")
_PUNCTUATION_ONLY_RE = re.compile(r"^[\W_]+$")
_REPEATED_PUNCT_RE = re.compile(r"([!?.|•·\-_=~*])\1{3,}")
_CHARSET_RE = re.compile(r"charset\s*=\s*['\"]?([a-zA-Z0-9._-]+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class WebsiteExtractionError(Exception):
    """Base exception for errors during website fetching or content extraction."""


class WebsiteFetchError(WebsiteExtractionError):
    """Raised when fetching a webpage fails due to HTTP, network, or SSL errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WebsiteTimeoutError(WebsiteFetchError):
    """Raised when connecting to or reading from a target website times out."""


class WebsiteAccessDeniedError(WebsiteFetchError):
    """Raised when the target website denies access or rate-limits requests."""


class UnsupportedContentTypeError(WebsiteExtractionError):
    """Raised when the target URL responds with a non-HTML content type."""


class WebsiteTooLargeError(WebsiteExtractionError):
    """Raised when a website response exceeds the configured byte size limit."""


class UnsafeRedirectError(WebsiteExtractionError):
    """Raised when a redirect is missing, malformed, looping, excessive, or unsafe."""


# ---------------------------------------------------------------------------
# Logging Helpers
# ---------------------------------------------------------------------------


def _sanitize_url_for_log(url: str) -> str:
    """Return a safe URL representation for logs (no credentials, bounded query)."""
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        netloc = f"{host}:{parsed.port}" if parsed.port else host
        query = parsed.query
        if len(query) > 80:
            query = f"{query[:77]}..."
        return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))
    except ValueError:
        return "<invalid-url>"


# ---------------------------------------------------------------------------
# Connection-Level SSRF & DNS Rebinding Protection (HTTPX / httpcore)
# ---------------------------------------------------------------------------


class PinnedSSRFSafeBackend(httpcore.AnyIOBackend):
    """Custom ``httpcore`` network backend that pins TCP connections to validated IPs.

    At TCP connect time, this backend resolves the target hostname, validates
    every returned IPv4/IPv6 address with :func:`validate_ip_address`, and dials
    a validated IP literal directly so the OS performs no second DNS lookup.
    ``httpcore`` preserves the original hostname for the HTTP ``Host`` header
    and TLS SNI / certificate verification.
    """

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        target_ips = await self._resolve_and_validate_target(host, port)

        last_connect_exc: Exception | None = None
        for ip_obj in target_ips:
            pinned_ip = str(ip_obj)
            try:
                return await super().connect_tcp(
                    host=pinned_ip,
                    port=port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_connect_exc = exc
                continue

        if last_connect_exc is not None:
            raise last_connect_exc
        raise httpcore.ConnectError(f"Unable to connect to any resolved IP for '{host}'.")

    @staticmethod
    async def _resolve_and_validate_target(
        host: str,
        port: int,
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """Validate an IP literal or resolve and validate all DNS records for host."""
        clean_host = host.strip("[]")
        try:
            ip_literal = ipaddress.ip_address(clean_host)
        except ValueError:
            ip_literal = None

        if ip_literal is not None:
            validate_ip_address(ip_literal)
            return [ip_literal]

        resolved_ips = await anyio.to_thread.run_sync(
            resolve_hostname_ips, clean_host, port
        )
        for resolved_ip in resolved_ips:
            validate_ip_address(resolved_ip)
        return resolved_ips


class SSRFSafeAsyncTransport(httpx.AsyncHTTPTransport):
    """``httpx.AsyncHTTPTransport`` backed by :class:`PinnedSSRFSafeBackend`."""

    def __init__(
        self,
        *,
        verify: ssl.SSLContext | str | bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: httpx.Limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
        ),
    ) -> None:
        super().__init__(
            verify=verify,
            trust_env=False,
            http1=http1,
            http2=http2,
            limits=limits,
            retries=0,
        )
        ssl_context = httpx.create_ssl_context(verify=verify, trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http1=http1,
            http2=http2,
            retries=0,
            network_backend=PinnedSSRFSafeBackend(),
        )


# ---------------------------------------------------------------------------
# Response Helpers
# ---------------------------------------------------------------------------


def _parse_content_type(header_value: str | None) -> tuple[str, str | None]:
    """Return ``(media_type, charset)`` from a ``Content-Type`` header."""
    if not header_value:
        return "", None
    media_type = header_value.split(";", 1)[0].strip().lower()
    charset_match = _CHARSET_RE.search(header_value)
    charset = charset_match.group(1).strip() if charset_match else None
    return media_type, charset


def _decode_html_bytes(
    raw_bytes: bytes,
    header_charset: str | None,
    fallback_encoding: str | None,
) -> str:
    """Decode downloaded HTML bytes safely without failing on invalid byte sequences."""
    for encoding in (header_charset, fallback_encoding, "utf-8"):
        if not encoding:
            continue
        try:
            return raw_bytes.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _is_ssl_error(exc: BaseException) -> bool:
    """Return True if an exception or its cause chain contains an SSL error."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ssl.SSLError):
            return True
        current = current.__cause__ or current.__context__
    return False


def _raise_for_http_status(status_code: int, safe_url: str) -> None:
    """Translate non-2xx HTTP status codes into structured extraction exceptions."""
    if 200 <= status_code < 300:
        return

    logger.warning(
        "Website fetch failed with HTTP status=%d url=%s", status_code, safe_url
    )

    if status_code == 403:
        raise WebsiteAccessDeniedError(
            "Access to the target website was denied (HTTP 403).",
            status_code=403,
        )
    if status_code == 429:
        raise WebsiteAccessDeniedError(
            "The target website rate-limited the request (HTTP 429).",
            status_code=429,
        )
    if status_code == 404:
        raise WebsiteFetchError(
            "The requested webpage was not found (HTTP 404).",
            status_code=404,
        )
    if status_code in (500, 502, 503, 504):
        raise WebsiteFetchError(
            f"The target website is currently unavailable (HTTP {status_code}).",
            status_code=status_code,
        )
    raise WebsiteFetchError(
        f"The target website returned an unexpected HTTP status ({status_code}).",
        status_code=status_code,
    )


async def _fetch_html(
    initial_url: str,
    *,
    timeout: float,
    max_response_bytes: int,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[str, int, str, str]:
    """Fetch HTML safely with manual redirect validation and bounded streaming.

    Returns:
        A tuple of ``(final_url, status_code, content_type, html_text)``.
    """
    current_url = initial_url
    visited_urls: set[str] = {current_url}
    redirect_count = 0

    http_timeout = httpx.Timeout(
        connect=min(5.0, timeout),
        read=timeout,
        write=min(5.0, timeout),
        pool=min(5.0, timeout),
    )
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
        "Accept-Language": "en-US,en;q=0.8",
    }

    owns_transport = transport is None
    active_transport = transport or SSRFSafeAsyncTransport()

    logger.info("Website fetch started url=%s", _sanitize_url_for_log(current_url))

    try:
        with anyio.fail_after(timeout):
            async with httpx.AsyncClient(
                transport=active_transport,
                timeout=http_timeout,
                headers=headers,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                while True:
                    safe_current_url = _sanitize_url_for_log(current_url)
                    try:
                        async with client.stream("GET", current_url) as response:
                            status_code = response.status_code

                            # Handle 3xx redirects manually
                            if status_code in REDIRECT_STATUS_CODES:
                                location = response.headers.get("location")
                                if not location or not location.strip():
                                    logger.warning(
                                        "Redirect missing Location header status=%d url=%s",
                                        status_code,
                                        safe_current_url,
                                    )
                                    raise UnsafeRedirectError(
                                        "Redirect response is missing a valid Location header."
                                    )

                                if redirect_count >= MAX_REDIRECTS:
                                    logger.warning(
                                        "Redirect limit exceeded (%d) url=%s",
                                        MAX_REDIRECTS,
                                        safe_current_url,
                                    )
                                    raise UnsafeRedirectError(
                                        f"Exceeded maximum number of redirects ({MAX_REDIRECTS})."
                                    )

                                try:
                                    next_url = await anyio.to_thread.run_sync(
                                        validate_redirect_url, current_url, location
                                    )
                                except URLValidationError as exc:
                                    logger.warning(
                                        "Unsafe destination rejected during redirect from url=%s",
                                        safe_current_url,
                                    )
                                    raise UnsafeRedirectError(
                                        "Redirect destination failed security validation."
                                    ) from exc

                                if next_url in visited_urls:
                                    logger.warning(
                                        "Redirect loop detected at url=%s",
                                        _sanitize_url_for_log(next_url),
                                    )
                                    raise UnsafeRedirectError(
                                        "Redirect loop detected while fetching the website."
                                    )

                                redirect_count += 1
                                visited_urls.add(next_url)
                                logger.info(
                                    "Redirect encountered (%d/%d) status=%d from=%s to=%s",
                                    redirect_count,
                                    MAX_REDIRECTS,
                                    status_code,
                                    safe_current_url,
                                    _sanitize_url_for_log(next_url),
                                )
                                current_url = next_url
                                continue

                            # Non-redirect response: validate status code
                            _raise_for_http_status(status_code, safe_current_url)

                            # Validate HTML content type
                            media_type, header_charset = _parse_content_type(
                                response.headers.get("content-type")
                            )
                            if media_type not in ALLOWED_CONTENT_TYPES:
                                logger.warning(
                                    "Unsupported content type '%s' url=%s",
                                    media_type or "unknown",
                                    safe_current_url,
                                )
                                raise UnsupportedContentTypeError(
                                    f"Unsupported content type '{media_type or 'unknown'}'. "
                                    "Only HTML documents are supported."
                                )

                            # Preliminary Content-Length check (never trusted exclusively)
                            raw_content_length = response.headers.get("content-length")
                            if raw_content_length is not None:
                                try:
                                    declared_size = int(raw_content_length.strip())
                                except ValueError:
                                    declared_size = -1
                                if declared_size > max_response_bytes:
                                    logger.warning(
                                        "Content too large (declared=%d limit=%d) url=%s",
                                        declared_size,
                                        max_response_bytes,
                                        safe_current_url,
                                    )
                                    raise WebsiteTooLargeError(
                                        "Website response exceeds the maximum allowed size."
                                    )

                            # Bounded streaming download (yield chunks immediately without re-buffering)
                            chunks: list[bytes] = []
                            total_bytes = 0
                            async for chunk in response.aiter_bytes():
                                if not chunk:
                                    continue
                                total_bytes += len(chunk)
                                if total_bytes > max_response_bytes:
                                    logger.warning(
                                        "Content too large while streaming (limit=%d) url=%s",
                                        max_response_bytes,
                                        safe_current_url,
                                    )
                                    raise WebsiteTooLargeError(
                                        "Website response exceeded the maximum allowed size."
                                    )
                                chunks.append(chunk)

                            raw_bytes = b"".join(chunks)
                            if not raw_bytes or not raw_bytes.strip():
                                logger.warning(
                                    "Empty response body url=%s", safe_current_url
                                )
                                raise WebsiteFetchError(
                                    "Target website returned an empty response.",
                                    status_code=status_code,
                                )

                            html_text = _decode_html_bytes(
                                raw_bytes, header_charset, response.encoding
                            )
                            logger.info(
                                "Fetch completed status=%d bytes=%d url=%s",
                                status_code,
                                total_bytes,
                                safe_current_url,
                            )
                            return current_url, status_code, media_type, html_text

                    except URLValidationError as exc:
                        logger.warning(
                            "Unsafe destination rejected during connection url=%s",
                            safe_current_url,
                        )
                        if redirect_count > 0:
                            raise UnsafeRedirectError(
                                "Redirect destination resolved to an unsafe network address."
                            ) from exc
                        raise
                    except httpx.TimeoutException as exc:
                        logger.warning("Request timed out url=%s", safe_current_url)
                        raise WebsiteTimeoutError(
                            "The request to the target website timed out."
                        ) from exc
                    except httpx.RequestError as exc:
                        if _is_ssl_error(exc):
                            logger.warning("SSL error url=%s", safe_current_url)
                            raise WebsiteFetchError(
                                "SSL/TLS verification failed while connecting to the target website."
                            ) from exc
                        logger.warning(
                            "Failed request (%s) url=%s",
                            type(exc).__name__,
                            safe_current_url,
                        )
                        raise WebsiteFetchError(
                            "Failed to fetch the target website due to a connection or protocol error."
                        ) from exc
                    except ssl.SSLError as exc:
                        logger.warning("SSL error url=%s", safe_current_url)
                        raise WebsiteFetchError(
                            "SSL/TLS verification failed while connecting to the target website."
                        ) from exc
    except TimeoutError as exc:
        logger.warning(
            "Overall request timeout exceeded url=%s",
            _sanitize_url_for_log(current_url),
        )
        raise WebsiteTimeoutError(
            "The request to the target website exceeded the overall timeout."
        ) from exc
    finally:
        if owns_transport:
            await active_transport.aclose()


# ---------------------------------------------------------------------------
# Content Cleaning & HTML Parsing
# ---------------------------------------------------------------------------


def _normalize_inline_text(text: str | None) -> str:
    """Collapse internal whitespace and strip outer spaces from an inline string."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_text(raw_text: str, *, max_length: int | None = None) -> str:
    """Clean extracted text into concise, deduplicated, LLM-ready prose.

    Args:
        raw_text: Uncleaned text extracted from HTML blocks.
        max_length: Optional maximum character length for the cleaned output.

    Returns:
        Normalized plain text without duplicate lines, boilerplate, or noise.
    """
    if not raw_text:
        return ""

    cleaned_lines: list[str] = []
    seen_lines: set[str] = set()

    for line in raw_text.splitlines():
        normalized = _normalize_inline_text(line)
        if not normalized:
            continue

        normalized = _REPEATED_PUNCT_RE.sub(r"\1", normalized)
        if _PUNCTUATION_ONLY_RE.match(normalized):
            continue

        lowered = normalized.lower()
        if lowered in _BOILERPLATE_LINES:
            continue

        if lowered in seen_lines:
            continue
        seen_lines.add(lowered)
        cleaned_lines.append(normalized)

    result = "\n\n".join(cleaned_lines)

    if max_length is not None and max_length > 0 and len(result) > max_length:
        truncated = result[:max_length].rstrip()
        # Avoid cutting cleanly in the middle of a word when possible
        last_space = truncated.rfind(" ")
        last_newline = truncated.rfind("\n")
        cut_index = max(last_space, last_newline)
        if cut_index > int(max_length * 0.8):
            truncated = truncated[:cut_index].rstrip()
        result = truncated

    return result


def _is_navigation_only_header(header_tag: Tag) -> bool:
    """Heuristic to decide whether a ``<header>`` is purely navigation chrome.

    Preserves headers that contain a primary ``<h1>`` heading or meaningful
    paragraph text so article/hero headers are not accidentally discarded.
    """
    if header_tag.find("h1") is not None:
        return False

    paragraphs = [
        _normalize_inline_text(p.get_text(" ", strip=True))
        for p in header_tag.find_all("p")
    ]
    if any(len(p) >= 40 for p in paragraphs):
        return False

    if header_tag.find("nav") is not None:
        return True

    total_text = _normalize_inline_text(header_tag.get_text(" ", strip=True))
    if not total_text:
        return True

    link_text = " ".join(
        _normalize_inline_text(a.get_text(" ", strip=True))
        for a in header_tag.find_all("a")
    )
    if len(link_text) / max(len(total_text), 1) >= 0.6:
        return True

    return False


def _is_irrelevant_aside(aside_tag: Tag) -> bool:
    """Heuristic to remove boilerplate/navigation sidebars while keeping rich callouts."""
    if aside_tag.find("nav") is not None or aside_tag.find("form") is not None:
        return True

    total_text = _normalize_inline_text(aside_tag.get_text(" ", strip=True))
    if len(total_text) < 60:
        return True

    link_text = " ".join(
        _normalize_inline_text(a.get_text(" ", strip=True))
        for a in aside_tag.find_all("a")
    )
    return (len(link_text) / max(len(total_text), 1)) >= 0.5


def _extract_meta_content(soup: BeautifulSoup, target_name: str) -> str | None:
    """Extract content from a ``<meta name=...>`` tag case-insensitively."""
    target_lower = target_name.lower()
    for meta in soup.find_all("meta"):
        name_attr = meta.get("name")
        if isinstance(name_attr, str) and name_attr.strip().lower() == target_lower:
            content = meta.get("content")
            if isinstance(content, str):
                cleaned = _normalize_inline_text(content)
                if cleaned:
                    return cleaned
    return None


def _extract_headings(soup: BeautifulSoup, tag_name: str) -> list[str]:
    """Extract ordered, deduplicated headings for a given heading level."""
    headings: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all(tag_name):
        text = _normalize_inline_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        headings.append(text)
        if len(headings) >= MAX_HEADINGS_PER_LEVEL:
            break
    return headings


def _normalize_site_host(hostname: str | None) -> str:
    """Normalize hostnames for internal vs. external link classification."""
    if not hostname:
        return ""
    host = hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _extract_links(
    soup: BeautifulSoup,
    final_url: str,
) -> tuple[list[ExtractedLink], list[ExtractedLink]]:
    """Extract deduplicated, relevant internal and external HTTP(S) links."""
    base_host = _normalize_site_host(urlsplit(final_url).hostname)
    internal_links: list[ExtractedLink] = []
    external_links: list[ExtractedLink] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        raw_href = anchor.get("href")
        if not isinstance(raw_href, str):
            continue
        href = raw_href.strip()
        if not href or href.startswith("#"):
            continue

        lowered_href = href.lower()
        if lowered_href.startswith(("javascript:", "mailto:", "tel:", "data:", "blob:")):
            continue

        resolved = urljoin(final_url, href)
        parsed = urlsplit(resolved)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            continue

        # Normalize away client-side fragment for cleaner deduplication
        normalized_url = urlunsplit(
            (parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, "")
        )
        if normalized_url in seen_urls:
            continue

        link_text = _normalize_inline_text(anchor.get_text(" ", strip=True))
        if not link_text:
            aria_label = anchor.get("aria-label") or anchor.get("title")
            link_text = _normalize_inline_text(
                aria_label if isinstance(aria_label, str) else ""
            )
        if not link_text:
            continue

        target_host = _normalize_site_host(parsed.hostname)
        is_internal = bool(base_host) and target_host == base_host

        if is_internal:
            if len(internal_links) >= MAX_INTERNAL_LINKS:
                continue
            internal_links.append(
                ExtractedLink(text=link_text, url=normalized_url, is_internal=True)
            )
        else:
            if len(external_links) >= MAX_EXTERNAL_LINKS:
                continue
            external_links.append(
                ExtractedLink(text=link_text, url=normalized_url, is_internal=False)
            )

        seen_urls.add(normalized_url)

    return internal_links, external_links


def _extract_images(
    soup: BeautifulSoup,
    final_url: str,
) -> tuple[list[str], list[ExtractedImage]]:
    """Extract limited image alt texts and URLs without downloading any images."""
    alt_texts: list[str] = []
    images: list[ExtractedImage] = []
    seen_alts: set[str] = set()

    for img in soup.find_all("img"):
        raw_alt = img.get("alt")
        if not isinstance(raw_alt, str):
            continue
        alt_text = _normalize_inline_text(raw_alt)
        if not alt_text:
            continue

        alt_key = alt_text.lower()
        if alt_key in seen_alts:
            continue
        seen_alts.add(alt_key)

        image_url: str | None = None
        raw_src = img.get("src")
        if isinstance(raw_src, str):
            src = raw_src.strip()
            if src and not src.lower().startswith(("data:", "blob:", "javascript:")):
                resolved = urljoin(final_url, src)
                if urlsplit(resolved).scheme.lower() in ("http", "https"):
                    image_url = resolved

        alt_texts.append(alt_text)
        images.append(ExtractedImage(alt=alt_text, url=image_url))

        if len(images) >= MAX_IMAGES:
            break

    return alt_texts, images


def parse_html(
    html: str,
    *,
    requested_url: str,
    final_url: str,
    status_code: int,
    content_type: str,
    max_content_length: int | None = None,
) -> WebsiteExtractedData:
    """Parse raw HTML and return cleaned, structured :class:`WebsiteExtractedData`."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract document metadata prior to DOM pruning
    title_tag = soup.find("title")
    title = (
        _normalize_inline_text(title_tag.get_text(" ", strip=True))
        if title_tag is not None
        else None
    ) or None

    meta_description = _extract_meta_content(soup, "description")

    raw_keywords = _extract_meta_content(soup, "keywords")
    meta_keywords: list[str] = []
    if raw_keywords:
        seen_kw: set[str] = set()
        for kw in raw_keywords.split(","):
            cleaned_kw = _normalize_inline_text(kw)
            if cleaned_kw and cleaned_kw.lower() not in seen_kw:
                seen_kw.add(cleaned_kw.lower())
                meta_keywords.append(cleaned_kw)

    # Remove non-readable active/style tags before link/image/heading extraction
    for tag in soup.find_all(["script", "style", "noscript", "template"]):
        tag.decompose()

    internal_links, external_links = _extract_links(soup, final_url)
    image_alt_texts, images = _extract_images(soup, final_url)

    # Evaluate header/aside heuristics before removing nav/form tags inside them
    for header_tag in list(soup.find_all("header")):
        if _is_navigation_only_header(header_tag):
            header_tag.decompose()

    for aside_tag in list(soup.find_all("aside")):
        if _is_irrelevant_aside(aside_tag):
            aside_tag.decompose()

    # Prune remaining non-content elements for clean main text and headings
    for tag in soup.find_all(list(ALWAYS_REMOVE_TAGS)):
        tag.decompose()

    h1_headings = _extract_headings(soup, "h1")
    h2_headings = _extract_headings(soup, "h2")
    h3_headings = _extract_headings(soup, "h3")

    root_node: Any = soup.body if soup.body is not None else soup
    raw_text = root_node.get_text(separator="\n")
    effective_limit = (
        max_content_length
        if max_content_length is not None
        else settings.max_content_length
    )
    main_text = clean_text(raw_text, max_length=effective_limit)

    return WebsiteExtractedData(
        requested_url=requested_url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        title=title,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        h1_headings=h1_headings,
        h2_headings=h2_headings,
        h3_headings=h3_headings,
        main_text=main_text,
        internal_links=internal_links,
        external_links=external_links,
        image_alt_texts=image_alt_texts,
        images=images,
        content_length=len(main_text),
    )


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------


async def extract_website(
    url: str,
    *,
    timeout: float | None = None,
    max_response_bytes: int | None = None,
    max_content_length: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> WebsiteExtractedData:
    """Validate, fetch, parse, and clean a publicly accessible website.

    Args:
        url: Submitted website URL to validate and extract.
        timeout: Optional timeout override in seconds (defaults to
            ``settings.request_timeout``).
        max_response_bytes: Optional max download size override in bytes
            (defaults to ``settings.max_response_bytes``).
        max_content_length: Optional max cleaned text length override in
            characters (defaults to ``settings.max_content_length``).
        transport: Optional custom ``httpx.AsyncBaseTransport`` (primarily for
            deterministic unit tests using ``httpx.MockTransport``).

    Returns:
        Structured :class:`WebsiteExtractedData` ready for downstream analysis.

    Raises:
        URLValidationError: If the initial URL fails validation or SSRF checks.
        WebsiteExtractionError: (or a more specific subclass) if fetching,
            redirecting, size checking, or content validation fails.
    """
    try:
        validated_url = await anyio.to_thread.run_sync(validate_url, url)
    except URLValidationError:
        logger.warning(
            "Unsafe destination rejected url=%s", _sanitize_url_for_log(url)
        )
        raise

    effective_timeout = float(
        timeout if timeout is not None else settings.request_timeout
    )
    effective_max_bytes = (
        max_response_bytes
        if max_response_bytes is not None
        else settings.max_response_bytes
    )
    effective_max_content = (
        max_content_length
        if max_content_length is not None
        else settings.max_content_length
    )

    final_url, status_code, content_type, html = await _fetch_html(
        validated_url,
        timeout=effective_timeout,
        max_response_bytes=effective_max_bytes,
        transport=transport,
    )

    extracted = parse_html(
        html,
        requested_url=validated_url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        max_content_length=effective_max_content,
    )

    logger.info(
        "Extraction completed url=%s status=%d content_length=%d",
        _sanitize_url_for_log(extracted.final_url),
        extracted.status_code,
        extracted.content_length,
    )

    return extracted
