"""Unit tests for URL validation, SSRF protection, DNS checks, and redirects."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.schemas import LinkAnalysisRequest
from app.utils.validators import (
    URLValidationError,
    validate_redirect_url,
    validate_url,
)


def _make_addrinfo(ips: list[str], port: int = 443) -> list[tuple]:
    """Build synthetic socket.getaddrinfo return tuples for testing."""
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


@pytest.fixture
def mock_public_dns():
    """Mock DNS resolution to always return a public IPv4 address."""
    with patch(
        "app.utils.validators.socket.getaddrinfo",
        return_value=_make_addrinfo(["93.184.216.34"]),
    ) as mock_getaddrinfo:
        yield mock_getaddrinfo


# ---------------------------------------------------------------------------
# Valid URL tests
# ---------------------------------------------------------------------------


class TestValidURLs:
    """Verify publicly accessible HTTP/HTTPS URLs are accepted and normalized."""

    @pytest.mark.parametrize(
        ("raw_url", "expected"),
        [
            ("https://example.com", "https://example.com"),
            ("http://example.org", "http://example.org"),
            ("https://www.python.org/", "https://www.python.org/"),
            ("https://subdomain.example.com/path", "https://subdomain.example.com/path"),
            (
                "https://example.com/page?query=test",
                "https://example.com/page?query=test",
            ),
            (
                "  HTTPS://Example.COM:443/path?a=1#section  ",
                "https://example.com/path?a=1",
            ),
            ("http://example.org:80/docs", "http://example.org/docs"),
            ("https://example.com:8443/api", "https://example.com:8443/api"),
            ("https://example.com./about", "https://example.com/about"),
        ],
    )
    def test_valid_domain_urls(self, mock_public_dns, raw_url: str, expected: str):
        assert validate_url(raw_url) == expected

    def test_valid_public_ipv4_address(self):
        # Public IP literal does not need DNS lookup
        with patch("app.utils.validators.socket.getaddrinfo") as mock_dns:
            assert validate_url("https://93.184.216.34/info") == "https://93.184.216.34/info"
            mock_dns.assert_not_called()

    def test_valid_public_ipv6_address(self):
        with patch("app.utils.validators.socket.getaddrinfo") as mock_dns:
            url = "https://[2606:2800:220:1:248:1893:25c8:1946]/"
            assert validate_url(url) == url
            mock_dns.assert_not_called()


# ---------------------------------------------------------------------------
# Invalid URL & SSRF tests
# ---------------------------------------------------------------------------


class TestInvalidURLs:
    """Verify malformed URLs, disallowed schemes, credentials, and SSRF targets fail."""

    @pytest.mark.parametrize(
        "bad_url",
        [
            "",
            "   ",
            "\t\n",
            "not-a-url",
            "example.com",
            "http:example.com",
            "https:/example.com",
            "https://",
            "https:///path-only",
            "https://example.com/has space",
            "https://example.com/\r\nInjected: header",
            "https://evil.com\\@127.0.0.1",
            "https://-badhost.example.com",
            "https://bad..example.com",
            "https://intranet/admin",
        ],
    )
    def test_malformed_and_empty_urls_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError):
            validate_url(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        [
            "ftp://example.com",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "data:text/html,<h1>hello</h1>",
            "gopher://example.com:70/",
            "ws://example.com/socket",
        ],
    )
    def test_unsupported_protocols_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError, match="Unsupported URL protocol"):
            validate_url(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://user:password@example.com",
            "https://admin@example.com",
            "https://:secret@example.com",
        ],
    )
    def test_embedded_credentials_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError, match="credentials"):
            validate_url(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        [
            "https://example.com:0",
            "https://example.com:65536",
            "https://example.com:99999",
            "https://example.com:abc",
            "https://example.com:",
            "https://example.com:-80",
        ],
    )
    def test_invalid_ports_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError, match="port"):
            validate_url(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://localhost",
            "http://localhost:8000",
            "https://localhost.",
            "http://localhost.localdomain",
            "http://app.localhost",
            "http://sub.api.localhost/test",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://service.internal",
            "http://printer.local",
        ],
    )
    def test_localhost_and_internal_hostnames_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError, match="local or internal"):
            validate_url(bad_url)

    @pytest.mark.parametrize(
        "bad_url",
        [
            # IPv4 loopback
            "http://127.0.0.1",
            "http://127.0.0.1:4000",
            "http://127.255.255.254",
            # IPv4 private ranges (RFC 1918)
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://172.31.255.254",
            "http://192.168.1.1",
            # IPv4 link-local & cloud metadata
            "http://169.254.1.1",
            "http://169.254.169.254",
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.170.2/v2/credentials",
            "http://100.100.100.200/latest/meta-data/",
            # IPv4 CGNAT, unspecified, multicast, reserved
            "http://100.64.0.1",
            "http://0.0.0.0",
            "http://224.0.0.1",
            "http://240.0.0.1",
            # IPv6 loopback, unspecified, private, link-local, multicast, metadata
            "http://[::1]",
            "http://[::]",
            "http://[fc00::1]",
            "http://[fd00:ec2::254]",
            "http://[fe80::1]",
            "http://[ff02::1]",
            # IPv4-mapped, NAT64, IPv4-translated, 6to4 IPv6 SSRF bypasses
            "http://[::ffff:127.0.0.1]",
            "http://[::ffff:169.254.169.254]",
            "http://[::ffff:10.0.0.1]",
            "http://[64:ff9b::127.0.0.1]",
            "http://[::ffff:0:127.0.0.1]",
            "http://[2002:7f00:0001::1]",
            # Obfuscated non-canonical IPv4 literals
            "http://2130706433",
            "http://0177.0.0.1",
            "http://0x7f.0x00.0x00.0x01",
            "http://127.1",
        ],
    )
    def test_unsafe_and_obfuscated_ips_rejected(self, bad_url: str):
        with pytest.raises(URLValidationError):
            validate_url(bad_url)


# ---------------------------------------------------------------------------
# DNS Resolution Validation tests (mocked)
# ---------------------------------------------------------------------------


class TestDNSResolutionValidation:
    """Verify DNS resolution inspection without external network dependencies."""

    def test_hostname_resolving_to_public_ip_succeeds(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"]),
        ):
            assert validate_url("https://example.com") == "https://example.com"

    def test_hostname_resolving_to_private_ip_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["192.168.1.10"]),
        ):
            with pytest.raises(URLValidationError, match="private IP"):
                validate_url("https://internal.example.com")

    def test_hostname_resolving_to_cloud_metadata_ip_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["169.254.169.254"]),
        ):
            with pytest.raises(URLValidationError, match="cloud metadata"):
                validate_url("https://metadata-alias.example.com")

    def test_hostname_resolving_to_mixed_public_and_private_ips_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["93.184.216.34", "10.0.0.5"]),
        ):
            with pytest.raises(URLValidationError, match="private IP"):
                validate_url("https://dual-homed.example.com")

    def test_hostname_resolving_to_ipv4_mapped_ipv6_loopback_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["::ffff:127.0.0.1"]),
        ):
            with pytest.raises(URLValidationError, match="loopback"):
                validate_url("https://mapped-loopback.example.com")

    def test_dns_resolution_failure_handled_gracefully(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            side_effect=socket.gaierror(8, "nodename nor servname provided"),
        ):
            with pytest.raises(URLValidationError, match="Failed to resolve hostname"):
                validate_url("https://nonexistent.invalid")

    def test_dns_empty_result_handled_gracefully(self):
        with patch("app.utils.validators.socket.getaddrinfo", return_value=[]):
            with pytest.raises(URLValidationError, match="did not resolve"):
                validate_url("https://empty-dns.example.com")


# ---------------------------------------------------------------------------
# Redirect Security tests
# ---------------------------------------------------------------------------


class TestRedirectSecurity:
    """Verify redirect destinations are re-validated against SSRF rules."""

    def test_valid_relative_redirect_accepted(self, mock_public_dns):
        target = validate_redirect_url("https://example.com/start", "/final?ok=1")
        assert target == "https://example.com/final?ok=1"

    def test_valid_cross_domain_redirect_accepted(self, mock_public_dns):
        target = validate_redirect_url(
            "https://example.com", "https://www.python.org/downloads/"
        )
        assert target == "https://www.python.org/downloads/"

    @pytest.mark.parametrize(
        "malicious_location",
        [
            "",
            "   ",
            "http://localhost/admin",
            "http://127.0.0.1:8080/internal",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/secret",
            "file:///etc/passwd",
            "//127.0.0.1/protocol-relative",
        ],
    )
    def test_unsafe_redirect_rejected(self, malicious_location: str):
        with pytest.raises(URLValidationError):
            validate_redirect_url("https://example.com/page", malicious_location)

    def test_redirect_to_domain_resolving_to_private_ip_rejected(self):
        with patch(
            "app.utils.validators.socket.getaddrinfo",
            return_value=_make_addrinfo(["172.16.0.10"]),
        ):
            with pytest.raises(URLValidationError, match="private IP"):
                validate_redirect_url(
                    "https://example.com", "https://rebound.example.com/secret"
                )


# ---------------------------------------------------------------------------
# Pydantic LinkAnalysisRequest integration tests
# ---------------------------------------------------------------------------


class TestLinkAnalysisRequestSchema:
    """Verify Pydantic schema integrates cleanly with validate_url."""

    def test_schema_accepts_and_normalizes_valid_url(self, mock_public_dns):
        payload = LinkAnalysisRequest(url="  HTTPS://Example.COM/page?q=1#top  ")
        assert payload.url == "https://example.com/page?q=1"

    def test_schema_requires_url_field(self):
        with pytest.raises(ValidationError):
            LinkAnalysisRequest()  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",
            "   ",
            "not-a-url",
            "ftp://example.com",
            "http://localhost",
            "http://169.254.169.254",
            "http://user:pass@example.com",
        ],
    )
    def test_schema_rejects_invalid_and_unsafe_urls(self, invalid_url: str):
        with pytest.raises(ValidationError):
            LinkAnalysisRequest(url=invalid_url)

