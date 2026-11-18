"""Reusable URL validation and SSRF protection utilities.

Security architecture notes
---------------------------
1. **DNS Rebinding Limitation**:
   Validating DNS records here (via ``socket.getaddrinfo``) provides strong
   defense-in-depth against SSRF, but DNS validation performed *before* an HTTP
   client opens a socket cannot by itself eliminate Time-of-Check to Time-of-Use
   (TOCTOU) DNS rebinding attacks. An attacker controlling an authoritative
   nameserver with a very short or zero TTL could return a public IP during
   validation and an internal/private IP (e.g., ``127.0.0.1`` or
   ``169.254.169.254``) milliseconds later when the HTTP client resolves the
   hostname again to establish a TCP connection.

   Therefore, the future website-fetching service (Phase 3) MUST also validate
   the actual resolved destination IP at connection time (for example, by using
   a custom HTTPX transport/socket hook that verifies the peer IP before
   connecting, or by pinning the validated IP while preserving the ``Host``
   header and TLS SNI).

2. **Redirect Security Strategy**:
   The future HTTPX website-fetching service MUST NOT enable blind automatic
   redirects (i.e., always configure ``httpx.AsyncClient(follow_redirects=False)``).
   Instead, it should manually inspect 3xx responses up to ``MAX_REDIRECTS`` hops
   and pass each ``Location`` header through :func:`validate_redirect_url` before
   issuing the next request. This ensures a public URL cannot redirect the
   fetcher to ``localhost``, private networks, cloud metadata endpoints, or
   unsupported schemes.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})
DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}
MAX_URL_LENGTH: int = 2048
MAX_HOSTNAME_LENGTH: int = 253
MAX_REDIRECTS: int = 5

# Explicit localhost and internal/cloud metadata hostnames
BLOCKED_EXACT_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

BLOCKED_HOSTNAME_SUFFIXES: tuple[str, ...] = (
    ".localhost",
    ".localhost.localdomain",
    ".local",
    ".internal",
    ".localdomain",
)

# Well-known cloud metadata IP addresses (AWS, GCP, Azure, ECS, Alibaba Cloud)
CLOUD_METADATA_IPS: frozenset[IPAddress] = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("169.254.170.2"),
        ipaddress.ip_address("100.100.100.200"),
        ipaddress.ip_address("fd00:ec2::254"),
    }
)

# Additional special-purpose networks that can embed or route to internal IPv4 targets
BLOCKED_SPECIAL_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-Grade NAT (RFC 6598)
    ipaddress.ip_network("64:ff9b::/96"),    # NAT64 Well-Known Prefix (RFC 6052)
    ipaddress.ip_network("64:ff9b:1::/48"),  # NAT64 Local-Use Prefix (RFC 8215)
    ipaddress.ip_network("::ffff:0:0/96"),   # IPv4-translated addresses (RFC 2765)
)

# RFC 1035 / 1123 hostname label: 1-63 chars of a-z, 0-9, or hyphen (not leading/trailing)
_HOSTNAME_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class URLValidationError(ValueError):
    """Raised when a URL fails syntax, protocol, or SSRF security validation."""


def _contains_control_or_whitespace(value: str) -> bool:
    """Return True if value contains whitespace or ASCII control characters."""
    return any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _has_empty_port(netloc: str) -> bool:
    """Return True if netloc specifies a trailing colon with an empty port."""
    # Strip IPv6 bracketed host if present before checking for port separator
    if netloc.startswith("["):
        closing_idx = netloc.find("]")
        if closing_idx == -1:
            return False
        remainder = netloc[closing_idx + 1 :]
        return remainder == ":"
    return netloc.endswith(":")


def validate_ip_address(ip: IPAddress) -> None:
    """Validate that an IP address is publicly routable and safe from SSRF.

    Raises:
        URLValidationError: If the IP belongs to any private, loopback,
            link-local, multicast, reserved, unspecified, cloud metadata, or
            non-global address range (including IPv4-mapped/tunneled IPv6).
    """
    # Unwrap IPv4 addresses embedded inside IPv6 addresses
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            validate_ip_address(ip.ipv4_mapped)
            return
        if ip.sixtofour is not None:
            validate_ip_address(ip.sixtofour)
        if ip.teredo is not None:
            server_ip, client_ip = ip.teredo
            validate_ip_address(server_ip)
            validate_ip_address(client_ip)

    if ip in CLOUD_METADATA_IPS:
        raise URLValidationError(
            f"Access to cloud metadata IP address '{ip}' is not allowed."
        )
    if ip.is_loopback:
        raise URLValidationError(
            f"Access to loopback IP address '{ip}' is not allowed."
        )
    if ip.is_link_local:
        raise URLValidationError(
            f"Access to link-local IP address '{ip}' is not allowed."
        )
    if ip.is_unspecified:
        raise URLValidationError(
            f"Access to unspecified IP address '{ip}' is not allowed."
        )
    if ip.is_private:
        raise URLValidationError(
            f"Access to private IP address '{ip}' is not allowed."
        )
    if ip.is_multicast:
        raise URLValidationError(
            f"Access to multicast IP address '{ip}' is not allowed."
        )
    if ip.is_reserved:
        raise URLValidationError(
            f"Access to reserved IP address '{ip}' is not allowed."
        )
    if any(ip in network for network in BLOCKED_SPECIAL_NETWORKS):
        raise URLValidationError(
            f"Access to restricted special-purpose IP address '{ip}' is not allowed."
        )
    if not ip.is_global:
        raise URLValidationError(
            f"Access to non-public IP address '{ip}' is not allowed."
        )


def _try_parse_ip(hostname: str) -> IPAddress | None:
    """Return a parsed IPAddress if hostname is an IP literal, else None."""
    if "%" in hostname:
        if ":" in hostname:
            raise URLValidationError(
                "IPv6 addresses with zone identifiers are not allowed."
            )
        raise URLValidationError(
            "Percent-encoded characters are not allowed in hostnames."
        )
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _normalize_and_validate_hostname(raw_hostname: str) -> tuple[str, IPAddress | None]:
    """Normalize and validate a hostname, rejecting malformed or local hosts.

    Returns:
        A tuple of ``(normalized_hostname, parsed_ip_or_none)``.
    """
    if not raw_hostname:
        raise URLValidationError("URL must include a valid hostname.")

    # Reject consecutive dots or leading dots before stripping a single trailing FQDN dot
    if ".." in raw_hostname or raw_hostname.startswith("."):
        raise URLValidationError(f"Malformed hostname '{raw_hostname}'.")

    hostname = raw_hostname.rstrip(".").lower()
    if not hostname:
        raise URLValidationError("URL must include a valid hostname.")

    # Check if hostname is an IP literal first
    parsed_ip = _try_parse_ip(hostname)
    if parsed_ip is not None:
        validate_ip_address(parsed_ip)
        return str(parsed_ip), parsed_ip

    # Convert internationalized domain names to ASCII Punycode
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise URLValidationError(f"Malformed hostname '{raw_hostname}'.") from exc

    if len(ascii_hostname) > MAX_HOSTNAME_LENGTH:
        raise URLValidationError(
            f"Hostname exceeds maximum length of {MAX_HOSTNAME_LENGTH} characters."
        )

    # Block localhost and known internal/metadata hostname patterns
    if ascii_hostname in BLOCKED_EXACT_HOSTNAMES or ascii_hostname.endswith(
        BLOCKED_HOSTNAME_SUFFIXES
    ):
        raise URLValidationError(
            f"Access to local or internal hostname '{ascii_hostname}' is not allowed."
        )

    # Reject non-canonical/obfuscated IPv4 literals (e.g. 0x7f.0x00.0x00.0x01, 0177.0.0.1, 127.1)
    try:
        socket.inet_aton(ascii_hostname)
    except OSError:
        pass
    else:
        raise URLValidationError(
            f"Non-standard IP address format '{raw_hostname}' is not allowed."
        )

    labels = ascii_hostname.split(".")
    if len(labels) < 2:
        raise URLValidationError(
            f"Hostname '{ascii_hostname}' must be a valid public domain name."
        )

    for label in labels:
        if not _HOSTNAME_LABEL_RE.match(label):
            raise URLValidationError(f"Malformed hostname '{raw_hostname}'.")

    # Reject all-numeric TLDs (blocks obfuscated IPv4 forms such as 127.1 or 0177.0.0.1)
    tld = labels[-1]
    if tld.isdigit() or len(tld) < 2:
        raise URLValidationError(f"Malformed hostname '{raw_hostname}'.")

    return ascii_hostname, None


def resolve_hostname_ips(hostname: str, port: int) -> list[IPAddress]:
    """Resolve IPv4 and IPv6 addresses for a hostname via system DNS.

    Raises:
        URLValidationError: If DNS resolution fails or returns no addresses.
    """
    try:
        addr_info = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except (socket.gaierror, OSError) as exc:
        raise URLValidationError(
            f"Failed to resolve hostname '{hostname}' via DNS."
        ) from exc

    resolved_ips: list[IPAddress] = []
    seen: set[IPAddress] = set()

    for _family, _socktype, _proto, _canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        # Strip IPv6 scope ID if present in OS resolver response (e.g. fe80::1%en0)
        if "%" in ip_str:
            ip_str = ip_str.split("%", 1)[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise URLValidationError(
                f"Hostname '{hostname}' resolved to an invalid IP address '{ip_str}'."
            ) from exc

        if ip_obj not in seen:
            seen.add(ip_obj)
            resolved_ips.append(ip_obj)

    if not resolved_ips:
        raise URLValidationError(
            f"Hostname '{hostname}' did not resolve to any IP addresses."
        )

    return resolved_ips


def _build_normalized_netloc(
    hostname: str,
    port: int | None,
    scheme: str,
    is_ipv6: bool,
) -> str:
    """Reconstruct a normalized authority (host[:port]) omitting default ports."""
    host_part = f"[{hostname}]" if is_ipv6 else hostname
    if port is not None and port != DEFAULT_PORTS[scheme]:
        return f"{host_part}:{port}"
    return host_part


def validate_url(url: str) -> str:
    """Validate, SSRF-check, and normalize a submitted HTTP/HTTPS URL.

    Steps performed:
        1. Validate non-empty string input and reject control characters/whitespace.
        2. Parse safely with ``urllib.parse.urlsplit``.
        3. Enforce ``http`` or ``https`` scheme with explicit authority (``://``).
        4. Reject embedded credentials (username/password) and parser-confusing
           backslashes in the authority component.
        5. Validate optional port number (1-65535) and reject empty port syntax.
        6. Normalize and validate hostname (rejecting localhost, internal suffixes,
           malformed labels, and obfuscated numeric IPs).
        7. If hostname is an IP literal, verify it is publicly routable and safe.
        8. Otherwise resolve all IPv4/IPv6 DNS records and verify every resolved IP
           is publicly routable and safe.
        9. Return a normalized URL (lowercase scheme/host, default ports removed,
           fragment stripped).

    Note:
        DNS validation here does not eliminate DNS rebinding attacks by itself.
        The future HTTP fetching service must also verify the resolved destination
        IP at connection time.

    Args:
        url: The raw URL string submitted by the caller.

    Returns:
        The normalized, validated URL string.

    Raises:
        URLValidationError: If the URL is invalid or targets an unsafe destination.
    """
    if not isinstance(url, str):
        raise URLValidationError("URL must be a string.")

    cleaned_url = url.strip()
    if not cleaned_url:
        raise URLValidationError("URL cannot be empty or whitespace only.")

    if len(cleaned_url) > MAX_URL_LENGTH:
        raise URLValidationError(
            f"URL exceeds maximum length of {MAX_URL_LENGTH} characters."
        )

    if _contains_control_or_whitespace(cleaned_url):
        raise URLValidationError(
            "URL must not contain whitespace or control characters."
        )

    try:
        parsed = urlsplit(cleaned_url)
    except ValueError as exc:
        raise URLValidationError("Malformed URL syntax.") from exc

    scheme = parsed.scheme.lower()
    if not scheme:
        raise URLValidationError(
            "URL must include a valid protocol (http or https)."
        )
    if scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"Unsupported URL protocol '{scheme}'. Only http and https are allowed."
        )

    # Ensure authority syntax (scheme://host...) rather than scheme:host
    if not parsed.netloc or not cleaned_url.lower().startswith(f"{scheme}://"):
        raise URLValidationError("Malformed URL: missing hostname or '://' separator.")

    # Reject backslashes in authority to avoid RFC 3986 vs WHATWG parser differentials
    if "\\" in parsed.netloc:
        raise URLValidationError("Malformed URL: backslashes are not allowed in host.")

    # Reject embedded credentials (user:pass@host or user@host)
    if (
        parsed.username is not None
        or parsed.password is not None
        or "@" in parsed.netloc
    ):
        raise URLValidationError(
            "URLs containing embedded credentials are not allowed."
        )

    if _has_empty_port(parsed.netloc):
        raise URLValidationError("Invalid URL port: port number cannot be empty.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise URLValidationError(
            "Invalid URL port: port must be an integer between 1 and 65535."
        ) from exc

    if port is not None and not (1 <= port <= 65535):
        raise URLValidationError(
            "Invalid URL port: port must be between 1 and 65535."
        )

    raw_hostname = parsed.hostname or ""
    normalized_hostname, parsed_ip = _normalize_and_validate_hostname(raw_hostname)

    # Resolve and verify every DNS record when hostname is a domain name
    if parsed_ip is None:
        effective_port = port if port is not None else DEFAULT_PORTS[scheme]
        resolved_ips = resolve_hostname_ips(normalized_hostname, effective_port)
        for resolved_ip in resolved_ips:
            validate_ip_address(resolved_ip)

    is_ipv6 = isinstance(parsed_ip, ipaddress.IPv6Address)
    normalized_netloc = _build_normalized_netloc(
        hostname=normalized_hostname,
        port=port,
        scheme=scheme,
        is_ipv6=is_ipv6,
    )

    # Strip client-side fragment while preserving path and query string
    return urlunsplit((scheme, normalized_netloc, parsed.path, parsed.query, ""))


def validate_redirect_url(current_url: str, location: str) -> str:
    """Resolve and validate an HTTP redirect ``Location`` header safely.

    Designed for the future HTTPX fetching service (Phase 3), which must disable
    automatic redirects (``follow_redirects=False``) and validate every redirect
    hop explicitly using this function before following it.

    Args:
        current_url: The validated URL that returned the 3xx redirect response.
        location: The raw ``Location`` header value from the redirect response.

    Returns:
        The normalized, validated absolute destination URL.

    Raises:
        URLValidationError: If the redirect target is missing, malformed, uses an
            unsupported scheme, or points to an unsafe/internal destination.
    """
    if not isinstance(location, str) or not location.strip():
        raise URLValidationError("Redirect Location header cannot be empty.")

    raw_location = location.strip()
    if _contains_control_or_whitespace(raw_location):
        raise URLValidationError(
            "Redirect Location must not contain whitespace or control characters."
        )

    target_url = urljoin(current_url, raw_location)
    return validate_url(target_url)
