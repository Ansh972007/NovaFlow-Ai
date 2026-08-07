"""Run async coroutines from sync code safely (including inside a running event loop)."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="novaflow-async-bridge")


def run_coro_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Execute coroutine from sync context without nesting asyncio.run on active loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    def _run_in_thread() -> T:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            try:
                coro.close()
            except Exception:
                pass

    return _executor.submit(_run_in_thread).result()


def run_sync_from_async(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run sync callable from async context without blocking the event loop on nested loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn(*args, **kwargs)

    return _executor.submit(lambda: fn(*args, **kwargs)).result()
