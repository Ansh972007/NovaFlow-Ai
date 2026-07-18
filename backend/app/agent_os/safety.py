"""AgentOS safety — permissions, injection, limits."""

from __future__ import annotations

import re
from typing import Any

from app.services.agent_tools import BUILTIN_TOOLS


INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"system prompt",
    r"jailbreak",
    r"disregard (your )?rules",
]


def validate_tool_permissions(tool_ids: list[str], *, allowed: list[str] | None = None) -> tuple[list[str], list[str]]:
    allowed_set = set(allowed or BUILTIN_TOOLS.keys())
    valid = [t for t in tool_ids if t in allowed_set]
    rejected = [t for t in tool_ids if t not in allowed_set]
    return valid[:8], rejected


def scan_input(text: str) -> dict[str, Any]:
    lower = (text or "").lower()
    signals = [p for p in INJECTION_PATTERNS if re.search(p, lower)]
    return {
        "injection_detected": bool(signals),
        "signals": signals,
        "input_length": len(text or ""),
    }


def risk_score(
    *,
    tool_count: int,
    has_web_fetch: bool,
    injection_detected: bool,
    sensitive_action: bool = False,
) -> dict[str, Any]:
    score = 0.1
    if has_web_fetch:
        score += 0.2
    if tool_count > 4:
        score += 0.15
    if injection_detected:
        score += 0.4
    if sensitive_action:
        score += 0.25
    level = "low" if score < 0.3 else ("medium" if score < 0.6 else "high")
    return {"score": round(min(1.0, score), 2), "level": level, "requires_approval": level == "high"}
