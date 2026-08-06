"""In-flight workflow run cancellation tokens (chat stop_run)."""

from __future__ import annotations

import asyncio
from typing import Dict

_cancel_events: Dict[str, asyncio.Event] = {}


def _key(workspace_id: int, user_id: int) -> str:
    return f"{workspace_id}:{user_id}"


def register_run(workspace_id: int, user_id: int) -> asyncio.Event:
    ev = asyncio.Event()
    _cancel_events[_key(workspace_id, user_id)] = ev
    return ev


def request_cancel(workspace_id: int, user_id: int) -> bool:
    ev = _cancel_events.get(_key(workspace_id, user_id))
    if not ev:
        return False
    ev.set()
    return True


def clear_run(workspace_id: int, user_id: int) -> None:
    _cancel_events.pop(_key(workspace_id, user_id), None)
