"""Output validation — reject invalid structured output before returning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    content: str
    errors: list[str]


def validate_text_output(text: str, *, max_len: int = 128_000) -> ValidationResult:
    content = (text or "").strip()
    errors: list[str] = []
    if not content:
        errors.append("empty_output")
    if len(content) > max_len:
        content = content[:max_len]
        errors.append("truncated")
    return ValidationResult(ok=not errors or errors == ["truncated"], content=content, errors=errors)


def validate_json_output(text: str) -> ValidationResult:
    raw = (text or "").strip()
    if not raw:
        return ValidationResult(ok=False, content="", errors=["empty_output"])
    try:
        parsed = json.loads(raw)
        return ValidationResult(ok=True, content=json.dumps(parsed, ensure_ascii=False), errors=[])
    except json.JSONDecodeError:
        # Try to extract first JSON object/array
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if match:
            try:
                parsed = json.loads(match.group(1))
                return ValidationResult(
                    ok=True, content=json.dumps(parsed, ensure_ascii=False), errors=["extracted_json"]
                )
            except json.JSONDecodeError:
                pass
        return ValidationResult(ok=False, content=raw, errors=["invalid_json"])


def validate_markdown_output(text: str) -> ValidationResult:
    content = (text or "").strip()
    if not content:
        return ValidationResult(ok=False, content="", errors=["empty_output"])
    # Block obvious script injection in markdown responses
    if re.search(r"<\s*script\b", content, re.I):
        cleaned = re.sub(r"<\s*script[\s\S]*?</script>", "", content, flags=re.I)
        return ValidationResult(ok=True, content=cleaned.strip(), errors=["stripped_script"])
    return ValidationResult(ok=True, content=content, errors=[])


def validate_tool_results(results: list[dict[str, Any]]) -> ValidationResult:
    if not results:
        return ValidationResult(ok=True, content="", errors=[])
    lines = []
    for row in results:
        tid = row.get("tool") or "tool"
        result = str(row.get("result") or "")[:4000]
        lines.append(f"{tid}: {result}")
    return ValidationResult(ok=True, content="\n".join(lines), errors=[])
