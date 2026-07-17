"""SSRF protection for outbound HTTP (agents, webhooks, URL ingest)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.security.config import SSRF_ALLOW_PRIVATE, SSRF_ALLOWED_HOSTS

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
}


class SafeUrlError(ValueError):
    pass


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return True
    if ip.is_private or ip.is_unspecified:
        return not SSRF_ALLOW_PRIVATE
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return True
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return not SSRF_ALLOW_PRIVATE
    return False


def assert_safe_url(url: str, *, allow_http: bool = True) -> str:
    """Validate URL is safe for server-side fetch. Returns normalized URL or raises."""
    if not url or not isinstance(url, str):
        raise SafeUrlError("URL is required")
    raw = url.strip()
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    allowed_schemes = {"http", "https"} if allow_http else {"https"}
    if scheme not in allowed_schemes:
        raise SafeUrlError("Only http/https URLs are allowed")
    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        raise SafeUrlError("URL host is required")
    if host in BLOCKED_HOSTNAMES:
        raise SafeUrlError("URL host is blocked")
    if host.endswith(".local") or host.endswith(".internal") or host.endswith(".localhost"):
        raise SafeUrlError("Internal hostnames are blocked")
    if SSRF_ALLOWED_HOSTS and host not in SSRF_ALLOWED_HOSTS:
        raise SafeUrlError("URL host is not in the allowlist")

    try:
        infos = socket.getaddrinfo(
            host,
            parsed.port or (443 if scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise SafeUrlError(f"Unable to resolve host: {exc}") from exc

    if not infos:
        raise SafeUrlError("Unable to resolve host")

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise SafeUrlError("URL resolves to a blocked or private address")

    try:
        literal = ipaddress.ip_address(host)
        if _is_blocked_ip(literal):
            raise SafeUrlError("URL uses a blocked IP address")
    except ValueError:
        pass

    return raw
