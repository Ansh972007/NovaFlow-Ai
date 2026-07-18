"""Distributed tracing — trace ID propagation via contextvars."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_stack: ContextVar[list[str]] = ContextVar("span_stack", default=[])


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def get_trace_id() -> str:
    tid = _trace_id.get()
    if not tid:
        tid = new_trace_id()
        _trace_id.set(tid)
    return tid


def set_trace_id(trace_id: str) -> None:
    _trace_id.set((trace_id or new_trace_id())[:32])


def push_span(name: str) -> None:
    stack = list(_span_stack.get())
    stack.append(name)
    _span_stack.set(stack)


def pop_span() -> str | None:
    stack = list(_span_stack.get())
    if not stack:
        return None
    span = stack.pop()
    _span_stack.set(stack)
    return span


def current_path() -> str:
    return " → ".join(_span_stack.get()) or "root"


def trace_context() -> dict[str, Any]:
    return {"trace_id": get_trace_id(), "path": current_path()}
