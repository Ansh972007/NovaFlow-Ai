"""In-process sliding-window rate limiter with Redis-ready interface."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple


class RateLimiter:
    """Thread-safe fixed-window counter. Keyed by (bucket, identity)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    def allow(
        self,
        bucket: str,
        identity: str,
        *,
        limit: int,
        window_seconds: int = 60,
        workspace_id: int | None = None,
    ) -> bool:
        if limit <= 0:
            return True
        if workspace_id is not None:
            identity = f"ws:{workspace_id}:{identity}"
        now = time.monotonic()
        key = (bucket, identity)
        with self._lock:
            q = self._hits[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def remaining(self, bucket: str, identity: str, *, limit: int, window_seconds: int = 60) -> int:
        now = time.monotonic()
        key = (bucket, identity)
        with self._lock:
            q = self._hits[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            return max(0, limit - len(q))


rate_limiter = RateLimiter()
