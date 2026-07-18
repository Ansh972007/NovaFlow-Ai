"""HTTP tracing middleware — propagates X-Trace-Id on every request."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.platform_intelligence.tracing.context import get_trace_id, set_trace_id


class TraceMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Trace-Id"

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = (request.headers.get(self.HEADER) or request.headers.get("x-request-id") or "").strip()
        set_trace_id(incoming or "")
        trace_id = get_trace_id()
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[self.HEADER] = trace_id
            return response
        finally:
            latency_ms = (time.perf_counter() - start) * 1000.0
            try:
                from app.platform_intelligence.observability.metrics import record_http_metric

                record_http_metric(
                    path=request.url.path,
                    method=request.method,
                    status=status,
                    latency_ms=latency_ms,
                    trace_id=trace_id,
                )
            except Exception:
                pass
