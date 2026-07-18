"""KOS indexing engine — chunk, embed, reindex with change detection."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.services.knowledge import process_file_record


def _chunk_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def index_document(
    db: Session,
    record: KnowledgeFile,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> dict[str, Any]:
    """Full index pipeline — delegates to existing process_file_record then stamps KOS metadata."""
    process_file_record(db, record, chunk_size, chunk_overlap)
    db.refresh(record)
    chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == record.id).all()
    for chunk in chunks:
        if hasattr(chunk, "content_hash"):
            chunk.content_hash = _chunk_hash(chunk.text)
        if hasattr(chunk, "version_no"):
            chunk.version_no = getattr(record, "version_no", None) or 1
    db.commit()
    return {
        "file_id": record.id,
        "status": record.status,
        "chunk_count": len(chunks),
        "version_no": getattr(record, "version_no", None) or 1,
    }


def reindex_collection(
    db: Session,
    kb: KnowledgeBase,
    *,
    partial: bool = False,
    file_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Reindex all or selected documents in a collection."""
    q = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id)
    if partial and file_ids:
        q = q.filter(KnowledgeFile.id.in_(file_ids))
    files = q.all()
    results = []
    for f in files:
        if f.status == 3 or partial:
            f.status = 5
            db.commit()
        results.append(index_document(db, f))
    return {"collection_id": kb.id, "reindexed": len(results), "files": results}


def detect_duplicates(db: Session, *, knowledge_id: int) -> list[dict]:
    """Find duplicate chunks by content hash within a collection."""
    if not hasattr(KnowledgeChunk, "content_hash"):
        return []
    rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.knowledge_id == knowledge_id).all()
    seen: dict[str, list[int]] = {}
    for row in rows:
        h = getattr(row, "content_hash", None) or _chunk_hash(row.text)
        seen.setdefault(h, []).append(row.id)
    dupes = [{"hash": h, "chunk_ids": ids} for h, ids in seen.items() if len(ids) > 1]
    return dupes[:50]
