"""Edge-case QA tests for the Phase 3 Website Extraction Engine."""

from __future__ import annotations

import asyncio
import gzip
import socket
from unittest.mock import patch

import httpx
import pytest

from app.services.website_extractor import (
    WebsiteAccessDeniedError,
    WebsiteFetchError,
    WebsiteTimeoutError,
    WebsiteTooLargeError,
    extract_website,
    parse_html,
)


def _run(coro):
    return asyncio.run(coro)


def _public_addrinfo(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


@pytest.fixture
def mock_public_dns():
    with patch(
        "app.utils.validators.socket.getaddrinfo", side_effect=_public_addrinfo
    ):
        yield


class TestHTMLEdgeCases:
    """Verify resilient parsing of malformed, minimal, Unicode, and noisy HTML."""

    def test_malformed_html_without_body_or_headings(self):
        malformed = "<p>Unclosed paragraph<div>Nested badly<span>Still readable text"
        extracted = parse_html(
            malformed,
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
        )
        assert extracted.title is None
        assert extracted.meta_description is None
        assert extracted.h1_headings == []
        assert "Unclosed paragraph" in extracted.main_text
        assert "Still readable text" in extracted.main_text

    def test_unicode_emoji_and_unusual_whitespace_preserved_cleanly(self):
        html = (
            "<html><head><title>Café\u00a0Analytics 🚀</title></head>"
            "<body><h1>München\u200b Cloud Solutions 🌐</h1>"
            "<p>Fast\u00a0\u00a0insights for global teams in 日本語 and Español.</p>"
            "</body></html>"
        )
        extracted = parse_html(
            html,
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
        )
        assert extracted.title == "Café Analytics 🚀"
        assert extracted.h1_headings == ["München Cloud Solutions 🌐"]
        assert "Fast insights for global teams in 日本語 and Español." in extracted.main_text

    def test_deeply_nested_and_script_style_heavy_html(self):
        nested_open = "<div>" * 40
        nested_close = "</div>" * 40
        html = (
            "<html><head>"
            + "<style>.a{color:red;}</style>" * 20
            + "<script>var x = 'noise';</script>" * 20
            + f"</head><body>{nested_open}<p>Core business value statement.</p>{nested_close}</body></html>"
        )
        extracted = parse_html(
            html,
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
        )
        assert extracted.main_text == "Core business value statement."


class TestHTTPAndStreamingEdgeCases:
    """Verify gzip handling, 303/307/308 redirects, 400/401/504, slow streams, and concurrency."""

    @pytest.mark.parametrize("status_code", [303, 307, 308])
    def test_redirect_status_codes_303_307_308_followed_safely(
        self, mock_public_dns, status_code: int
    ):
        def handler(req: httpx.Request) -> httpx.Response:
            if req.url.path in ("", "/"):
                return httpx.Response(status_code, headers={"location": "/target"})
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Target</title></head><body><p>Reached target</p></body></html>",
            )

        result = _run(
            extract_website("https://example.com", transport=httpx.MockTransport(handler))
        )
        assert result.final_url == "https://example.com/target"
        assert result.title == "Target"

    def test_http_401_raises_access_denied_error(self, mock_public_dns):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                401, headers={"content-type": "text/html"}, text="Unauthorized"
            )
        )
        with pytest.raises(WebsiteAccessDeniedError) as exc_info:
            _run(extract_website("https://example.com", transport=transport))
        assert exc_info.value.status_code == 401

    @pytest.mark.parametrize("status_code", [400, 504])
    def test_http_400_and_504_raise_fetch_error(self, mock_public_dns, status_code: int):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                status_code, headers={"content-type": "text/html"}, text="Error"
            )
        )
        with pytest.raises(WebsiteFetchError) as exc_info:
            _run(extract_website("https://example.com", transport=transport))
        assert exc_info.value.status_code == status_code

    def test_valid_gzip_response_decoded_and_extracted(self, mock_public_dns):
        raw_html = b"<html><head><title>Compressed</title></head><body><p>Gzipped content works.</p></body></html>"
        compressed = gzip.compress(raw_html)
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html; charset=utf-8",
                    "content-encoding": "gzip",
                    "content-length": str(len(compressed)),
                },
                content=compressed,
            )
        )
        result = _run(extract_website("https://example.com", transport=transport))
        assert result.title == "Compressed"
        assert "Gzipped content works." in result.main_text

    def test_gzip_bomb_blocked_when_decompressed_bytes_exceed_limit(
        self, mock_public_dns
    ):
        huge_html = b"<html><body><p>" + (b"A" * 100_000) + b"</p></body></html>"
        compressed = gzip.compress(huge_html)
        assert len(compressed) < 1000  # Wire size looks tiny
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                headers={
                    "content-type": "text/html",
                    "content-encoding": "gzip",
                    "content-length": str(len(compressed)),
                },
                content=compressed,
            )
        )
        with pytest.raises(WebsiteTooLargeError):
            _run(
                extract_website(
                    "https://example.com",
                    max_response_bytes=5000,
                    transport=transport,
                )
            )

    def test_slow_stream_exceeding_overall_timeout_raises_website_timeout(
        self, mock_public_dns
    ):
        class _SlowStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b"<html><body><p>Start"
                await asyncio.sleep(0.25)
                yield b"End</p></body></html>"

        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200, headers={"content-type": "text/html"}, stream=_SlowStream()
            )
        )
        with pytest.raises(WebsiteTimeoutError):
            _run(
                extract_website(
                    "https://example.com",
                    timeout=0.05,
                    transport=transport,
                )
            )

    def test_concurrent_extractions_remain_isolated(self, mock_public_dns):
        def handler(req: httpx.Request) -> httpx.Response:
            slug = req.url.path.strip("/") or "root"
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=f"<html><head><title>Page {slug}</title></head><body><p>Body {slug}</p></body></html>",
            )

        async def run_batch():
            transport = httpx.MockTransport(handler)
            return await asyncio.gather(
                extract_website("https://example.com/one", transport=transport),
                extract_website("https://example.com/two", transport=transport),
                extract_website("https://example.com/three", transport=transport),
            )

        results = _run(run_batch())
        assert [r.title for r in results] == ["Page one", "Page two", "Page three"]

