"""
Outbound-request SSRF guard.

Anything that lets an LLM choose a URL to fetch (the [FETCH: url] tool in
reasoning.py) is a remote SSRF trigger: the URL choice is steered by search
results and page content an attacker can influence, not typed by a trusted
user. This module is the single choke point that decides whether a URL is
safe to request before any outbound connection is made.
"""
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

# Hostnames that resolve to "here" regardless of DNS - block outright rather
# than relying solely on IP inspection.
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}

# Cloud metadata endpoints. Most already fall inside link-local (169.254/16)
# or are otherwise private, but they're listed explicitly so the intent is
# unmistakable and the check doesn't depend on that being true forever.
_BLOCKED_IPS = {
    "169.254.169.254",  # AWS / Azure / GCP metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}


class UnsafeUrlError(ValueError):
    """Raised when a URL fails the outbound-request safety check."""


def _is_blocked_ip(ip_str: str) -> bool:
    if ip_str in _BLOCKED_IPS:
        return True
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Unparseable -> treat as unsafe.
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve_ips(hostname: str) -> set:
    infos = socket.getaddrinfo(hostname, None)
    return {info[4][0] for info in infos}


def check_url_is_safe(url: str) -> None:
    """
    Raises UnsafeUrlError if `url` must not be fetched: non-http(s) scheme,
    missing host, a blocked hostname, or a hostname that resolves (on any
    of its A/AAAA records) to a private/loopback/link-local/reserved IP or
    a known cloud metadata address.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise UnsafeUrlError(f"could not parse URL: {exc}") from exc

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"disallowed URL scheme {parsed.scheme!r}")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeUrlError("URL has no host")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise UnsafeUrlError(f"blocked hostname {hostname!r}")

    try:
        ips = _resolve_ips(hostname)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"DNS resolution failed for {hostname!r}: {exc}") from exc

    if not ips:
        raise UnsafeUrlError(f"no addresses resolved for {hostname!r}")

    for ip in ips:
        if _is_blocked_ip(ip):
            raise UnsafeUrlError(f"{hostname!r} resolves to disallowed address {ip}")


def is_url_safe(url: str) -> bool:
    try:
        check_url_is_safe(url)
        return True
    except UnsafeUrlError:
        return False
