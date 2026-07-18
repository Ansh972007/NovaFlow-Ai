"""KOS parsing engine — text, tables, OCR, metadata extraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session


def detect_document_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    mapping = {
        "pdf": "pdf",
        "docx": "word",
        "doc": "word",
        "xlsx": "excel",
        "xlsm": "excel",
        "csv": "csv",
        "tsv": "csv",
        "md": "markdown",
        "txt": "text",
        "html": "html",
        "htm": "html",
        "json": "json",
        "xml": "xml",
        "pptx": "powerpoint",
        "ppt": "powerpoint",
        "zip": "zip",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "gif": "image",
        "webp": "image",
    }
    if suffix in mapping:
        return mapping[suffix]
    if suffix in {"py", "js", "ts", "java", "go", "rs", "cpp", "c", "h"}:
        return "source_code"
    return "unknown"


def parse_document(path: Path, db: Session | None = None) -> dict[str, Any]:
    """Extract text and structured metadata from a document."""
    from app.services.knowledge import extract_text

    doc_type = detect_document_type(path)
    text = extract_text(path, db)
    headings = _extract_headings(text, doc_type)
    sections = _extract_sections(text, headings)
    metadata = {
        "document_type": doc_type,
        "char_count": len(text),
        "word_count": len(re.findall(r"\w+", text)),
        "heading_count": len(headings),
        "section_count": len(sections),
    }
    return {
        "text": text,
        "document_type": doc_type,
        "headings": headings,
        "sections": sections,
        "metadata": metadata,
    }


def _extract_headings(text: str, doc_type: str) -> list[str]:
    headings: list[str] = []
    if doc_type == "markdown":
        for line in text.splitlines():
            if line.startswith("#"):
                headings.append(line.lstrip("#").strip())
    else:
        for line in text.splitlines()[:200]:
            stripped = line.strip()
            if stripped and len(stripped) < 120 and stripped.isupper():
                headings.append(stripped)
    return headings[:50]


def _extract_sections(text: str, headings: list[str]) -> list[dict]:
    if not headings:
        return [{"title": "body", "text": text[:4000]}]
    sections = []
    for i, h in enumerate(headings):
        start = text.find(h)
        if start < 0:
            continue
        end = text.find(headings[i + 1], start + len(h)) if i + 1 < len(headings) else len(text)
        sections.append({"title": h, "text": text[start:end][:4000]})
    return sections[:30] or [{"title": "body", "text": text[:4000]}]
