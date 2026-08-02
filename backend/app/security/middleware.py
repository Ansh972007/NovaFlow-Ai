"""HTTP security headers + request hardening middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.security.config import (
    CORS_ALLOWED_ORIGINS,
    MAX_REQUEST_BODY_BYTES,
    RATE_LIMIT_API_PER_MINUTE,
    RATE_LIMIT_LOGIN_PER_MINUTE,
    RATE_LIMIT_UPLOAD_PER_MINUTE,
)
from app.security.rate_limit import rate_limiter


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "")[:64]
    return ""


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Body size guard for non-streaming
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        {"status_code": 413, "status_message": "Request body too large", "data": None},
                        status_code=413,
                    )
            except ValueError:
                pass

        ip = client_ip(request) or "unknown"
        path = request.url.path or ""

        # Auth endpoints — strict limit
        if path.endswith("/user/login") or path.endswith("/user/regist"):
            if not rate_limiter.allow("login", ip, limit=RATE_LIMIT_LOGIN_PER_MINUTE, window_seconds=60):
                return JSONResponse(
                    {"status_code": 429, "status_message": "Too many login attempts. Try again later.", "data": None},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        elif "/knowledge/upload" in path:
            if not rate_limiter.allow("upload", ip, limit=RATE_LIMIT_UPLOAD_PER_MINUTE, window_seconds=60):
                return JSONResponse(
                    {"status_code": 429, "status_message": "Upload rate limit exceeded", "data": None},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        elif path.startswith("/api/"):
            identity = request.headers.get("authorization", ip)[:80]
            if not rate_limiter.allow("api", identity, limit=RATE_LIMIT_API_PER_MINUTE, window_seconds=60):
                return JSONResponse(
                    {"status_code": 429, "status_message": "API rate limit exceeded", "data": None},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )

        response: Response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        # HSTS only meaningful over HTTPS terminators
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        # Reflect allowed origin only (strict CORS handled by CORSMiddleware config)
        origin = request.headers.get("origin")
        if origin and origin in CORS_ALLOWED_ORIGINS:
            response.headers.setdefault("Vary", "Origin")
        return response


import logging
import traceback
import uuid

logger = logging.getLogger("novaflow.errors")

class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            ref_id = uuid.uuid4().hex[:8].upper()
            logger.error(
                f"[Ref: {ref_id}] Unhandled Exception: {str(exc)}\n"
                f"{traceback.format_exc()}"
            )
            return JSONResponse(
                {
                    "status_code": 500,
                    "status_message": f"An internal server error occurred. Reference ID: {ref_id}",
                    "data": None,
                },
                status_code=500,
            )
