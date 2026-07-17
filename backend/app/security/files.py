"""Secure file upload validation — extension, MIME sniff, magic bytes, sanitization."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from app.security.config import MAX_UPLOAD_BYTES

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".html",
    ".htm",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}

# Magic-byte signatures (prefix)
_MAGIC = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": None,  # zip-based office — validated by extension
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"RIFF": None,  # webp starts RIFF....WEBP
}


class FileSecurityError(ValueError):
    pass


def sanitize_filename(name: str) -> str:
    base = Path(name or "upload.bin").name
    base = base.replace("\x00", "")
    base = re.sub(r"[^\w.\- ()\[\]]+", "_", base, flags=re.UNICODE)
    base = base.strip(". ")[:180] or "upload.bin"
    if ".." in base or "/" in base or "\\" in base:
        base = "upload.bin"
    return base


def extension_of(name: str) -> str:
    return Path(name).suffix.lower()


def validate_upload(
    *,
    filename: str,
    content: bytes,
    content_type: Optional[str] = None,
) -> dict:
    """Validate upload bytes. Returns {safe_name, ext, size}."""
    if content is None:
        raise FileSecurityError("Empty upload")
    size = len(content)
    if size <= 0:
        raise FileSecurityError("Empty upload")
    if size > MAX_UPLOAD_BYTES:
        raise FileSecurityError(f"File exceeds maximum size of {MAX_UPLOAD_BYTES} bytes")

    safe = sanitize_filename(filename)
    ext = extension_of(safe)
    if ext not in ALLOWED_EXTENSIONS:
        raise FileSecurityError(f"File type {ext or '(none)'} is not allowed")

    head = content[:16]
    # Reject executable / script prefixes
    if head.startswith(b"MZ") or head.startswith(b"\x7fELF"):
        raise FileSecurityError("Executable files are not allowed")
    if head.lstrip().startswith(b"#!"):
        raise FileSecurityError("Script files are not allowed")

    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise FileSecurityError("File content is not a valid PDF")
    if ext in {".png"} and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise FileSecurityError("File content is not a valid PNG")
    if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise FileSecurityError("File content is not a valid JPEG")
    if ext in {".docx", ".xlsx", ".pptx"} and not content.startswith(b"PK"):
        raise FileSecurityError("Office document must be a valid OpenXML package")
    if ext == ".webp":
        if not (content.startswith(b"RIFF") and b"WEBP" in content[:16]):
            raise FileSecurityError("File content is not a valid WEBP")

    # Soft MIME check when provided
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in {"application/x-msdownload", "application/x-executable", "application/x-sh"}:
            raise FileSecurityError("MIME type is not allowed")

    storage_name = f"{uuid.uuid4().hex}_{safe}"
    return {"safe_name": safe, "storage_name": storage_name, "ext": ext, "size": size}
