"""KOS AI knowledge curator — quality and maintenance recommendations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.knowledge_os.indexing import detect_duplicates


def analyze_collection(db: Session, kb: KnowledgeBase) -> dict[str, Any]:
    """Evaluate collection health and return actionable recommendations."""
    files = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).all()
    chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.knowledge_id == kb.id).count()
    failed = [f for f in files if f.status == 3]
    stale_cutoff = datetime.utcnow() - timedelta(days=180)
    stale = [f for f in files if f.update_time and f.update_time < stale_cutoff]
    empty = [f for f in files if f.status == 2 and not db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == f.id).count()]
    dupes = detect_duplicates(db, knowledge_id=kb.id)

    recommendations = []
    if failed:
        recommendations.append({"action": "reindex", "reason": f"{len(failed)} failed documents", "file_ids": [f.id for f in failed[:10]]})
    if stale:
        recommendations.append({"action": "review", "reason": f"{len(stale)} documents older than 180 days"})
    if dupes:
        recommendations.append({"action": "merge", "reason": f"{len(dupes)} duplicate chunk groups detected"})
    if empty:
        recommendations.append({"action": "delete", "reason": f"{len(empty)} empty indexed documents"})
    if not getattr(kb, "owner_id", None):
        recommendations.append({"action": "assign_owner", "reason": "Collection has no owner"})
    if getattr(kb, "review_required", 0):
        recommendations.append({"action": "approve", "reason": "Collection requires review before publish"})

    weak_chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.knowledge_id == kb.id)
        .all()
    )
    short = [c for c in weak_chunks if len(c.text or "") < 40]
    if len(short) > 5:
        recommendations.append({"action": "reindex", "reason": f"{len(short)} low-quality short chunks"})

    return {
        "collection_id": kb.id,
        "document_count": len(files),
        "chunk_count": chunks,
        "failed_count": len(failed),
        "stale_count": len(stale),
        "duplicate_groups": len(dupes),
        "recommendations": recommendations,
        "score": _health_score(len(files), len(failed), len(dupes), len(short)),
    }


def _health_score(docs: int, failed: int, dupes: int, weak: int) -> float:
    if docs == 0:
        return 0.0
    penalty = (failed * 0.15 + dupes * 0.1 + weak * 0.02) / max(docs, 1)
    return round(max(0.0, min(1.0, 1.0 - penalty)), 2)


def workspace_analytics(db: Session, *, workspace_id: int) -> dict[str, Any]:
    """Workspace-level knowledge analytics."""
    collections = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id).all()
    total_docs = 0
    total_chunks = 0
    unused = []
    for kb in collections:
        doc_count = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).count()
        chunk_count = db.query(KnowledgeChunk).filter(KnowledgeChunk.knowledge_id == kb.id).count()
        total_docs += doc_count
        total_chunks += chunk_count
        if doc_count == 0:
            unused.append({"id": kb.id, "name": kb.name})
    return {
        "collection_count": len(collections),
        "document_count": total_docs,
        "chunk_count": total_chunks,
        "unused_collections": unused[:20],
        "avg_chunks_per_doc": round(total_chunks / max(total_docs, 1), 1),
    }
