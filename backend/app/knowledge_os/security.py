"""KOS security — classification, PII, compliance hooks."""

from __future__ import annotations

import re
from typing import Any

CLASSIFICATION_ORDER = ["public", "internal", "confidential", "restricted", "secret"]

PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
}


def classification_rank(level: str) -> int:
    try:
        return CLASSIFICATION_ORDER.index((level or "internal").lower())
    except ValueError:
        return 1


def can_access_classification(user_max: str, resource_level: str) -> bool:
    return classification_rank(user_max) >= classification_rank(resource_level)


def scan_text_for_pii(text: str) -> list[dict[str, Any]]:
    findings = []
    for kind, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text or ""):
            findings.append({"type": kind, "sample": match.group(0)[:20]})
            if len(findings) >= 20:
                return findings
    return findings


def scan_document_content(text: str, *, classification: str = "internal") -> dict[str, Any]:
    pii = scan_text_for_pii(text)
    injection_signals = []
    lower = (text or "")[:2000].lower()
    for phrase in ("ignore previous instructions", "system prompt", "jailbreak"):
        if phrase in lower:
            injection_signals.append(phrase)
    return {
        "classification": classification,
        "pii_count": len(pii),
        "pii_findings": pii[:5],
        "prompt_injection_signals": injection_signals,
        "compliance_pass": len(pii) == 0 and not injection_signals,
    }


def enforce_collection_access(
    *,
    workspace_id: int,
    collection_workspace_id: int,
    classification: str = "internal",
    user_classification_max: str = "restricted",
) -> bool:
    if collection_workspace_id != workspace_id:
        return False
    return can_access_classification(user_classification_max, classification)
