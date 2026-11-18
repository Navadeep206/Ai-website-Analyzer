"""Unit tests for the Phase 3 Website Extraction Engine.

All HTTP requests and DNS lookups are mocked so the suite is 100% deterministic
and never accesses external websites or networks.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from unittest.mock import AsyncMock, patch

import httpcore
import httpx
import pytest

from app.services.website_extractor import (
    PinnedSSRFSafeBackend,
    UnsafeRedirectError,
    UnsupportedContentTypeError,
    WebsiteAccessDeniedError,
    WebsiteFetchError,
    WebsiteTimeoutError,
    WebsiteTooLargeError,
    clean_text,
    extract_website,
    parse_html,
)
from app.utils.validators import URLValidationError


def _make_addrinfo(ips: list[str], port: int = 443) -> list[tuple]:
    """Build synthetic socket.getaddrinfo return tuples."""
    results = []
    for ip in ips:
        if ":" in ip:
            family = socket.AF_INET6
            sockaddr = (ip, port, 0, 0)
        else:
            family = socket.AF_INET
            sockaddr = (ip, port)
        results.append((family, socket.SOCK_STREAM, 6, "", sockaddr))
    return results


def _run(coro):
    """Run an async coroutine inside a synchronous pytest test."""
    return asyncio.run(coro)


@pytest.fixture
def mock_public_dns():
    """Mock DNS resolution to return a single public IPv4 address."""
    with patch(
        "app.utils.validators.socket.getaddrinfo",
        return_value=_make_addrinfo(["93.184.216.34"]),
    ) as mock_dns:
        yield mock_dns


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>   Acme Cloud   Analytics  </title>
    <meta NAME="Description" CONTENT="  AI-powered cloud   analytics for modern SaaS teams.  ">
    <meta name="KEYWORDS" content="cloud analytics, SaaS, AI insights, saas">
    <style>body { color: red; } .hidden { display: none; }</style>
    <script>console.log("tracking script should be removed");</script>
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/pricing">Pricing</a>
            <a href="/pricing#top">Pricing Duplicate</a>
            <a href="#section">Fragment Only</a>
            <a href="javascript:void(0)">JS Link</a>
            <a href="mailto:hello@acme.example">Email Us</a>
            <a href="tel:+15551234567">Call Us</a>
        </nav>
    </header>

    <header class="hero">
        <h1>Smarter Analytics for Growing SaaS Teams</h1>
        <p>Turn product telemetry into clear growth actions in minutes with automated insights.</p>
    </header>

    <main>
        <p>Skip to content</p>
        <h2>Core Capabilities</h2>
        <p>Acme Cloud Analytics monitors funnels, retention cohorts, and customer health scores.</p>
        <p>Acme Cloud Analytics monitors funnels, retention cohorts, and customer health scores.</p>

        <h3>Real-Time Dashboards</h3>
        <p>Track key revenue metrics with sub-second queries and customizable alerts.</p>
        <p>   </p>
        <p>|||||</p>

        <a href="/features/dashboards">Explore Dashboards</a>
        <a href="https://docs.partner.org/integration">Partner Docs</a>
        <a href="https://docs.partner.org/integration#api">Partner Docs Duplicate</a>
        <a href="/empty-text"></a>

        <img src="/assets/dashboard.png" alt="Real-time SaaS analytics dashboard" />
        <img src="https://cdn.example.com/team.jpg" alt="Analytics engineering team" />
        <img src="/assets/decorative.png" alt="" />
        <img src="data:image/png;base64,AAAA" alt="Inline chart preview" />

        <form><input type="email" /><button>Subscribe Now</button></form>
        <svg><text>SVG icon text</text></svg>
        <noscript>Enable JavaScript to run this app.</noscript>
    </main>

    <aside>
        <a href="/blog/1">Related Post 1</a>
        <a href="/blog/2">Related Post 2</a>
    </aside>

    <footer>
        <p>Copyright 2026 Acme Cloud Inc. All rights reserved.</p>
    </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 1. URL Validation Integration Tests
# ---------------------------------------------------------------------------


class TestURLValidationIntegration:
    """Verify extract_website enforces Phase 2 validation before fetching."""

    def test_valid_url_accepted(self, mock_public_dns):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="<html><head><title>OK</title></head><body><p>Hello world</p></body></html>",
            )
        )
        result = _run(extract_website("https://example.com", transport=transport))
        assert result.requested_url == "https://example.com"
        assert result.final_url == "https://example.com"
        assert result.status_code == 200
        assert result.title == "OK"

    @pytest.mark.parametrize(
        "invalid_url",
        ["", "   ", "not-a-url", "ftp://example.com", "file:///etc/passwd"],
    )
    def test_invalid_url_rejected_before_http_request(self, invalid_url: str):
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, text="<html></html>")

        with pytest.raises(URLValidationError):
            _run(extract_website(invalid_url, transport=httpx.MockTransport(handler)))
        assert not called

    @pytest.mark.parametrize(
        "unsafe_url",
        [
            "http://localhost",
            "http://127.0.0.1",
            "http://192.168.1.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://user:pass@example.com",
        ],
    )
    def test_unsafe_url_rejected_before_http_request(self, unsafe_url: str):
        called = False

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, text="<html></html>")

        with pytest.raises(URLValidationError):
            _run(extract_website(unsafe_url, transport=httpx.MockTransport(handler)))
        assert not called


# ---------------------------------------------------------------------------
# 2. HTTP Fetching & Response Validation Tests
# ---------------------------------------------------------------------------


class TestHTTPFetching:
    """Verify HTTP status, content type, timeout, network, and SSL handling."""

    def test_successful_html_response_and_user_agent(self, mock_public_dns):
        captured_headers: dict[str, str] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(req.headers))
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text=SAMPLE_HTML,
            )

        result = _run(
            extract_website("https://example.com", transport=httpx.MockTransport(handler))
        )
        assert result.status_code == 200
        assert result.content_type == "text/html"
        assert captured_headers.get("user-agent") == "AIWebsiteLinkAnalysisBot/1.0"

    def test_xhtml_content_type_supported(self, mock_public_dns):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={"content-type": "application/xhtml+xml; charset=utf-8"},
                text="<html><head><title>XHTML</title></head><body><p>Valid XHTML content</p></body></html>",
            )
        )
        result = _run(extract_website("https://example.com", transport=transport))
        assert result.content_type == "application/xhtml+xml"
        assert result.title == "XHTML"

    @pytest.mark.parametrize("status_code", [403, 429])
    def test_http_access_denied_and_rate_limit(self, mock_public_dns, status_code: int):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                status_code, headers={"content-type": "text/html"}, text="Blocked"
            )
        )
        with pytest.raises(WebsiteAccessDeniedError) as exc_info:
            _run(extract_website("https://example.com", transport=transport))
        assert exc_info.value.status_code == status_code

    @pytest.mark.parametrize("status_code", [404, 500, 502, 503])
    def test_http_error_statuses(self, mock_public_dns, status_code: int):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                status_code, headers={"content-type": "text/html"}, text="Error"
            )
        )
        with pytest.raises(WebsiteFetchError) as exc_info:
            _run(extract_website("https://example.com", transport=transport))
        assert exc_info.value.status_code == status_code

    @pytest.mark.parametrize(
        "timeout_exc",
        [httpx.ConnectTimeout("connect timed out"), httpx.ReadTimeout("read timed out")],
    )
    def test_timeout_errors(self, mock_public_dns, timeout_exc: Exception):
        def handler(req: httpx.Request) -> httpx.Response:
            raise timeout_exc

        with pytest.raises(WebsiteTimeoutError):
            _run(extract_website("https://example.com", transport=httpx.MockTransport(handler)))

    def test_connection_error(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        with pytest.raises(WebsiteFetchError, match="connection or protocol error"):
            _run(extract_website("https://example.com", transport=httpx.MockTransport(handler)))

    def test_ssl_error(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            ssl_exc = ssl.SSLCertVerificationError("certificate verify failed")
            raise httpx.ConnectError("SSL error") from ssl_exc

        with pytest.raises(WebsiteFetchError, match="SSL/TLS verification failed"):
            _run(extract_website("https://example.com", transport=httpx.MockTransport(handler)))

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/pdf",
            "application/json",
            "image/png",
            "video/mp4",
            "application/octet-stream",
            "text/plain",
            "",
        ],
    )
    def test_unsupported_content_types_rejected(self, mock_public_dns, content_type: str):
        headers = {"content-type": content_type} if content_type else {}
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, headers=headers, content=b"%PDF-1.7 binary")
        )
        with pytest.raises(UnsupportedContentTypeError):
            _run(extract_website("https://example.com", transport=transport))

    @pytest.mark.parametrize("body", [b"", b"   \n\t  "])
    def test_empty_response_rejected(self, mock_public_dns, body: bytes):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200, headers={"content-type": "text/html"}, content=body
            )
        )
        with pytest.raises(WebsiteFetchError, match="empty response"):
            _run(extract_website("https://example.com", transport=transport))


# ---------------------------------------------------------------------------
# 3. Redirect Security Tests
# ---------------------------------------------------------------------------


class TestRedirectHandling:
    """Verify manual redirect handling, limits, loop detection, and SSRF checks."""

    def test_valid_redirect(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            if str(req.url) == "https://example.com":
                return httpx.Response(
                    301, headers={"location": "https://www.example.com/home"}
                )
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Redirected</title></head><body><p>Welcome home</p></body></html>",
            )

        result = _run(
            extract_website("https://example.com", transport=httpx.MockTransport(handler))
        )
        assert result.requested_url == "https://example.com"
        assert result.final_url == "https://www.example.com/home"
        assert result.title == "Redirected"

    def test_relative_redirect(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path in ("", "/"):
                return httpx.Response(302, headers={"location": "/landing?ref=1"})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Landing</title></head><body><p>Landing page</p></body></html>",
            )

        result = _run(
            extract_website("https://example.com", transport=httpx.MockTransport(handler))
        )
        assert result.final_url == "https://example.com/landing?ref=1"

    def test_multiple_valid_redirects_within_limit(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            routes = {
                "https://example.com": "/step1",
                "https://example.com/step1": "/step2",
                "https://example.com/step2": "/step3",
            }
            url_str = str(req.url)
            if url_str in routes:
                return httpx.Response(302, headers={"location": routes[url_str]})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Final Step</title></head><body><p>Done</p></body></html>",
            )

        result = _run(
            extract_website("https://example.com", transport=httpx.MockTransport(handler))
        )
        assert result.final_url == "https://example.com/step3"
        assert result.title == "Final Step"

    def test_redirect_loop_rejected(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            if str(req.url) == "https://example.com":
                return httpx.Response(302, headers={"location": "https://example.com/a"})
            return httpx.Response(302, headers={"location": "https://example.com"})

        with pytest.raises(UnsafeRedirectError, match="loop"):
            _run(
                extract_website("https://example.com", transport=httpx.MockTransport(handler))
            )

    def test_redirect_limit_exceeded_rejected(self, mock_public_dns):
        hop = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal hop
            hop += 1
            return httpx.Response(302, headers={"location": f"/hop-{hop}"})

        with pytest.raises(UnsafeRedirectError, match="maximum number of redirects"):
            _run(
                extract_website("https://example.com", transport=httpx.MockTransport(handler))
            )

    @pytest.mark.parametrize(
        "unsafe_location",
        [
            "http://localhost/admin",
            "http://127.0.0.1:4000/health",
            "http://192.168.1.50/router",
            "http://10.0.0.1/internal",
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "ftp://example.com/file",
            "http://user:password@example.com/secret",
            "http://example.com:99999/badport",
        ],
    )
    def test_unsafe_redirect_targets_rejected(self, mock_public_dns, unsafe_location: str):
        requests_made = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal requests_made
            requests_made += 1
            return httpx.Response(302, headers={"location": unsafe_location})

        with pytest.raises(UnsafeRedirectError):
            _run(
                extract_website("https://example.com", transport=httpx.MockTransport(handler))
            )
        # Only the initial public request should have been issued
        assert requests_made == 1

    def test_missing_location_header_rejected(self, mock_public_dns):
        transport = httpx.MockTransport(lambda req: httpx.Response(302, headers={}))
        with pytest.raises(UnsafeRedirectError, match="Location"):
            _run(extract_website("https://example.com", transport=transport))

    def test_empty_location_header_rejected(self, mock_public_dns):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"location": "   "})
        )
        with pytest.raises(UnsafeRedirectError, match="Location"):
            _run(extract_website("https://example.com", transport=transport))


# ---------------------------------------------------------------------------
# 4. Response Size Protection Tests
# ---------------------------------------------------------------------------


class _CountingByteStream(httpx.AsyncByteStream):
    """Streaming response body that tracks how many chunks were consumed."""

    def __init__(self, chunk: bytes, count: int) -> None:
        self._chunk = chunk
        self._count = count
        self.chunks_yielded = 0

    async def __aiter__(self):
        for _ in range(self._count):
            self.chunks_yielded += 1
            yield self._chunk


class TestResponseSizeProtection:
    """Verify Content-Length checks and bounded streaming download limits."""

    def test_small_response_accepted(self, mock_public_dns):
        body = b"<html><head><title>Small</title></head><body><p>Tiny page</p></body></html>"
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": str(len(body)),
                },
                content=body,
            )
        )
        result = _run(
            extract_website(
                "https://example.com",
                max_response_bytes=1024,
                transport=transport,
            )
        )
        assert result.title == "Small"

    def test_content_length_exceeding_limit_rejected_early(self, mock_public_dns):
        stream = _CountingByteStream(b"a" * 512, count=20)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": "5000",
                },
                stream=stream,
            )
        )
        with pytest.raises(WebsiteTooLargeError):
            _run(
                extract_website(
                    "https://example.com",
                    max_response_bytes=1024,
                    transport=transport,
                )
            )
        # Should abort before consuming any stream chunks
        assert stream.chunks_yielded == 0

    def test_stream_exceeding_limit_without_content_length_stops_early(
        self, mock_public_dns
    ):
        stream = _CountingByteStream(b"x" * 400, count=50)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                stream=stream,
            )
        )
        with pytest.raises(WebsiteTooLargeError):
            _run(
                extract_website(
                    "https://example.com",
                    max_response_bytes=1000,
                    transport=transport,
                )
            )
        # Stopped as soon as 3rd chunk pushed total to 1200 > 1000 (not all 50 chunks)
        assert stream.chunks_yielded == 3

    def test_missing_content_length_within_limit_succeeds(self, mock_public_dns):
        stream = _CountingByteStream(
            b"<html><head><title>Streamed</title></head><body><p>OK</p></body></html>",
            count=1,
        )
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                stream=stream,
            )
        )
        result = _run(
            extract_website(
                "https://example.com",
                max_response_bytes=2048,
                transport=transport,
            )
        )
        assert result.title == "Streamed"

    def test_lying_content_length_still_caught_during_streaming(self, mock_public_dns):
        stream = _CountingByteStream(b"z" * 600, count=10)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": "50",  # Under-reported intentionally
                },
                stream=stream,
            )
        )
        with pytest.raises(WebsiteTooLargeError):
            _run(
                extract_website(
                    "https://example.com",
                    max_response_bytes=1000,
                    transport=transport,
                )
            )
        assert stream.chunks_yielded == 2

    def test_malformed_content_length_handled_gracefully(self, mock_public_dns):
        body = b"<html><head><title>OK</title></head><body><p>Body</p></body></html>"
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-length": "not-a-number",
                },
                content=body,
            )
        )
        result = _run(
            extract_website(
                "https://example.com",
                max_response_bytes=2048,
                transport=transport,
            )
        )
        assert result.title == "OK"


# ---------------------------------------------------------------------------
# 5. HTML Parsing & Content Cleaning Tests
# ---------------------------------------------------------------------------


class TestHTMLExtractionAndCleaning:
    """Verify structured extraction, boilerplate removal, and text cleaning."""

    def test_rich_html_extraction(self):
        extracted = parse_html(
            SAMPLE_HTML,
            requested_url="https://acme.example",
            final_url="https://acme.example",
            status_code=200,
            content_type="text/html",
            max_content_length=15000,
        )

        # Metadata
        assert extracted.title == "Acme Cloud Analytics"
        assert (
            extracted.meta_description
            == "AI-powered cloud analytics for modern SaaS teams."
        )
        assert extracted.meta_keywords == ["cloud analytics", "SaaS", "AI insights"]

        # Headings preserved in order
        assert extracted.h1_headings == ["Smarter Analytics for Growing SaaS Teams"]
        assert extracted.h2_headings == ["Core Capabilities"]
        assert extracted.h3_headings == ["Real-Time Dashboards"]

        # Hero header content kept, navigation/footer/script/style/form/svg/aside removed
        assert "Smarter Analytics for Growing SaaS Teams" in extracted.main_text
        assert (
            "Turn product telemetry into clear growth actions in minutes"
            in extracted.main_text
        )
        assert "Acme Cloud Analytics monitors funnels" in extracted.main_text
        assert "tracking script should be removed" not in extracted.main_text
        assert "color: red" not in extracted.main_text
        assert "Copyright 2026" not in extracted.main_text
        assert "Subscribe Now" not in extracted.main_text
        assert "SVG icon text" not in extracted.main_text
        assert "Enable JavaScript" not in extracted.main_text
        assert "Skip to content" not in extracted.main_text
        assert "Related Post 1" not in extracted.main_text
        assert "|||||" not in extracted.main_text

        # Duplicate paragraph removed
        assert (
            extracted.main_text.count("Acme Cloud Analytics monitors funnels") == 1
        )
        assert extracted.content_length == len(extracted.main_text)

        # Internal & external links resolved, filtered, and deduplicated
        internal_urls = [link.url for link in extracted.internal_links]
        external_urls = [link.url for link in extracted.external_links]
        assert "https://acme.example/pricing" in internal_urls
        assert "https://acme.example/features/dashboards" in internal_urls
        assert internal_urls.count("https://acme.example/pricing") == 1
        assert external_urls == ["https://docs.partner.org/integration"]
        assert all(link.is_internal for link in extracted.internal_links)
        assert all(not link.is_internal for link in extracted.external_links)

        # Filtered link schemes & empty text excluded
        all_urls = internal_urls + external_urls
        assert not any(
            u.startswith(("javascript:", "mailto:", "tel:")) for u in all_urls
        )
        assert "https://acme.example/empty-text" not in all_urls

        # Images extracted without downloading
        assert extracted.image_alt_texts == [
            "Real-time SaaS analytics dashboard",
            "Analytics engineering team",
            "Inline chart preview",
        ]
        assert extracted.images[0].url == "https://acme.example/assets/dashboard.png"
        assert extracted.images[1].url == "https://cdn.example.com/team.jpg"
        assert extracted.images[2].url is None  # data: URI excluded

    def test_missing_title_and_meta_return_none(self):
        extracted = parse_html(
            "<html><body><p>Simple body paragraph.</p></body></html>",
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
        )
        assert extracted.title is None
        assert extracted.meta_description is None
        assert extracted.meta_keywords == []
        assert extracted.main_text == "Simple body paragraph."

    def test_clean_text_enforces_max_length(self):
        long_text = " ".join(["analytics"] * 500)
        cleaned = clean_text(long_text, max_length=120)
        assert len(cleaned) <= 120
        assert cleaned.endswith("analytics")


# ---------------------------------------------------------------------------
# 6. DNS Security & Connection-Level IP Pinning Tests
# ---------------------------------------------------------------------------


class TestDNSSecurityAndPinning:
    """Verify DNS checks during initial validation, redirects, and TCP connect."""

    def test_dns_private_ip_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["192.168.0.10"]),
        ):
            with pytest.raises(URLValidationError, match="private IP"):
                _run(extract_website("https://internal.example.com"))

    def test_dns_mixed_public_and_private_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["93.184.216.34", "10.0.0.5"]),
        ):
            with pytest.raises(URLValidationError, match="private IP"):
                _run(extract_website("https://mixed.example.com"))

    def test_dns_failure_handled_gracefully(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            side_effect=socket.gaierror(8, "nodename nor servname provided"),
        ):
            with pytest.raises(URLValidationError, match="Failed to resolve"):
                _run(extract_website("https://nonexistent.invalid"))

    def test_redirect_destination_dns_resolving_to_private_ip_rejected(self):
        def fake_dns(host: str, port: int, *args, **kwargs):
            if host == "public.example.com":
                return _make_addrinfo(["93.184.216.34"], port)
            if host == "rebound.example.com":
                return _make_addrinfo(["172.16.0.42"], port)
            raise socket.gaierror(8, "unknown host")

        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                302, headers={"location": "https://rebound.example.com/secret"}
            )
        )
        with patch("app.utils.validators.socket.getaddrinfo", side_effect=fake_dns):
            with pytest.raises(UnsafeRedirectError):
                _run(
                    extract_website("https://public.example.com", transport=transport)
                )

    def test_pinned_backend_connects_directly_to_validated_ip(self):
        backend = PinnedSSRFSafeBackend()
        fake_stream = object()

        with (
            patch(
                "app.utils.validators.socket.getaddrinfo",
                return_value=_make_addrinfo(["93.184.216.34"], 443),
            ),
            patch.object(
                httpcore.AnyIOBackend,
                "connect_tcp",
                new=AsyncMock(return_value=fake_stream),
            ) as mock_super_connect,
        ):
            stream = _run(backend.connect_tcp("example.com", 443, timeout=5.0))
            assert stream is fake_stream
            # Must dial the validated IP literal, NOT the hostname
            mock_super_connect.assert_awaited_once_with(
                host="93.184.216.34",
                port=443,
                timeout=5.0,
                local_address=None,
                socket_options=None,
            )

    def test_pinned_backend_blocks_dns_rebinding_at_connect_time(self):
        backend = PinnedSSRFSafeBackend()

        with (
            patch(
                "app.utils.validators.socket.getaddrinfo",
                return_value=_make_addrinfo(["127.0.0.1"], 443),
            ),
            patch.object(
                httpcore.AnyIOBackend,
                "connect_tcp",
                new=AsyncMock(),
            ) as mock_super_connect,
        ):
            with pytest.raises(URLValidationError, match="loopback"):
                _run(backend.connect_tcp("rebind.example.com", 443, timeout=5.0))
            mock_super_connect.assert_not_awaited()

    def test_pinned_backend_falls_back_across_validated_ips(self):
        backend = PinnedSSRFSafeBackend()
        fake_stream = object()

        with (
            patch(
                "app.utils.validators.socket.getaddrinfo",
                return_value=_make_addrinfo(
                    ["2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"], 443
                ),
            ),
            patch.object(
                httpcore.AnyIOBackend,
                "connect_tcp",
                new=AsyncMock(
                    side_effect=[httpcore.ConnectError("IPv6 unreachable"), fake_stream]
                ),
            ) as mock_super_connect,
        ):
            stream = _run(backend.connect_tcp("example.com", 443, timeout=5.0))
            assert stream is fake_stream
            assert mock_super_connect.await_count == 2
            assert mock_super_connect.await_args_list[0].kwargs["host"] == (
                "2606:2800:220:1:248:1893:25c8:1946"
            )
            assert mock_super_connect.await_args_list[1].kwargs["host"] == "93.184.216.34"
