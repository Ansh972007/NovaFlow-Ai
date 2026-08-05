"""Durable chat ops registry — add-only spine for Powerhouse / Autopilot / Forge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

HandlerFn = Callable[..., Any | Awaitable[Any]]


@dataclass(frozen=True)
class OpSpec:
    id: str
    phrases: tuple[str, ...]  # regex patterns (case-insensitive) matched against full message
    card_type: str
    catalog_group: str  # powerhouse | autopilot | forge | core
    title: str = ""
    chip: str = ""
    priority: int = 100  # lower = matched first among registry ops


_REGISTRY: dict[str, OpSpec] = {}
_HANDLERS: dict[str, HandlerFn] = {}
_BOOTSTRAPPED = False


def register_op(
    spec: OpSpec,
    handler: HandlerFn | None = None,
) -> None:
    _REGISTRY[spec.id] = spec
    if handler is not None:
        _HANDLERS[spec.id] = handler


def register_ops(specs: list[tuple[OpSpec, HandlerFn | None]]) -> None:
    for spec, handler in specs:
        register_op(spec, handler)


def get_op(op_id: str) -> OpSpec | None:
    return _REGISTRY.get(op_id)


def list_ops(*, group: str | None = None) -> list[OpSpec]:
    rows = list(_REGISTRY.values())
    if group:
        rows = [o for o in rows if o.catalog_group == group]
    return sorted(rows, key=lambda o: (o.priority, o.id))


def catalog_tools(group: str) -> list[dict[str, Any]]:
    out = []
    for op in list_ops(group=group):
        if not op.chip or op.id.endswith("_catalog"):
            continue
        out.append(
            {
                "id": op.id,
                "title": op.title or op.id,
                "chip": op.chip,
                "card": op.card_type,
            }
        )
    return out


def classify_registered_intent(text: str) -> str | None:
    """Match message against registered OpSpec phrases. Prefer lower priority number, then longer match."""
    ensure_ops_bootstrapped()
    t = (text or "").lower().strip()
    if not t:
        return None
    best: tuple[int, int, str] | None = None  # (-priority, match_len, id) inverted for max
    for op in _REGISTRY.values():
        for pat in op.phrases:
            m = re.search(pat, t, flags=re.I)
            if not m:
                continue
            score = (-int(op.priority), len(m.group(0)), op.id)
            if best is None or score > best:
                best = score
    return best[2] if best else None


def get_handler(op_id: str) -> HandlerFn | None:
    ensure_ops_bootstrapped()
    return _HANDLERS.get(op_id)


def ensure_ops_bootstrapped() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True
    # Import side-effect registration (order: powerhouse → autopilot → forge)
    from app.composer import chat_powerhouse as _ph  # noqa: F401
    from app.composer import chat_autopilot as _ap  # noqa: F401
    from app.composer import chat_forge as _fg  # noqa: F401
    _ph.register_powerhouse_ops()
    _ap.register_autopilot_ops()
    _fg.register_forge_ops()


def reset_registry_for_tests() -> None:
    """Test helper — clears registry and allows re-bootstrap."""
    global _BOOTSTRAPPED
    _REGISTRY.clear()
    _HANDLERS.clear()
    _BOOTSTRAPPED = False
