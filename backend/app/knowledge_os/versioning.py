"""KOS version control — document versions, diff, restore."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import KnowledgeDocumentVersion, KnowledgeFile


def create_document_version(
    db: Session,
    record: KnowledgeFile,
    *,
    created_by: int | None = None,
    change_summary: str = "",
) -> KnowledgeDocumentVersion:
    version_no = (getattr(record, "version_no", None) or 0) + 1
    path = UPLOAD_DIR / record.file_path
    content_hash = ""
    if path.exists():
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    ver = KnowledgeDocumentVersion(
        file_id=record.id,
        version_no=version_no,
        content_hash=content_hash,
        file_path=record.file_path,
        change_summary=change_summary or f"Version {version_no}",
        created_by=created_by,
        approval_status="approved",
    )
    db.add(ver)
    if hasattr(record, "version_no"):
        record.version_no = version_no
    if hasattr(record, "content_hash"):
        record.content_hash = content_hash
    db.commit()
    db.refresh(ver)
    return ver


def list_versions(db: Session, file_id: int) -> list[dict]:
    rows = (
        db.query(KnowledgeDocumentVersion)
        .filter(KnowledgeDocumentVersion.file_id == file_id)
        .order_by(KnowledgeDocumentVersion.version_no.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "version_no": r.version_no,
            "content_hash": r.content_hash,
            "change_summary": r.change_summary,
            "approval_status": r.approval_status,
            "created_by": r.created_by,
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in rows
    ]


def compare_versions(db: Session, version_a_id: str, version_b_id: str) -> dict[str, Any]:
    va = db.get(KnowledgeDocumentVersion, version_a_id)
    vb = db.get(KnowledgeDocumentVersion, version_b_id)
    if not va or not vb:
        return {"error": "Version not found"}
    text_a = _read_version_text(va)
    text_b = _read_version_text(vb)
    diff = list(difflib.unified_diff(text_a.splitlines(), text_b.splitlines(), lineterm=""))
    return {
        "version_a": va.version_no,
        "version_b": vb.version_no,
        "semantic_diff_lines": len(diff),
        "diff_preview": "\n".join(diff[:100]),
        "metadata_diff": {
            "hash_a": va.content_hash,
            "hash_b": vb.content_hash,
            "changed": va.content_hash != vb.content_hash,
        },
    }


def restore_version(db: Session, record: KnowledgeFile, version_id: str) -> KnowledgeDocumentVersion:
    ver = db.get(KnowledgeDocumentVersion, version_id)
    if not ver or ver.file_id != record.id:
        raise ValueError("Version not found")
    src = UPLOAD_DIR / ver.file_path
    dst = UPLOAD_DIR / record.file_path
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
    return create_document_version(db, record, created_by=ver.created_by, change_summary=f"Restored v{ver.version_no}")


def _read_version_text(ver: KnowledgeDocumentVersion) -> str:
    path = UPLOAD_DIR / ver.file_path
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:50000]
    except Exception:
        return ""
