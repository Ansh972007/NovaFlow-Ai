"""Prompt-injection and AI output safety guards."""

from __future__ import annotations

import re
from typing import Optional

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+(prompts?|instructions?)", re.I),
    re.compile(r"you\s+are\s+now\s+(dan|jailbroken|unrestricted)", re.I),
    re.compile(r"system\s*:\s*you\s+are", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|hidden\s+instructions)", re.I),
    re.compile(r"exfiltrate|exfiltration", re.I),
]


def detect_prompt_injection(text: str) -> Optional[str]:
    """Return a short reason if text looks like prompt injection; else None."""
    if not text:
        return None
    sample = text[:8000]
    for pat in _INJECTION_PATTERNS:
        if pat.search(sample):
            return f"Blocked pattern: {pat.pattern[:60]}"
    # High density of instruction-override markers
    markers = len(re.findall(r"\b(ignore|disregard|override|jailbreak)\b", sample, re.I))
    if markers >= 4 and len(sample) < 2000:
        return "Suspicious instruction-override density"
    return None


def sanitize_user_prompt(text: str, *, max_len: int = 32000) -> str:
    cleaned = (text or "").replace("\x00", "")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned
