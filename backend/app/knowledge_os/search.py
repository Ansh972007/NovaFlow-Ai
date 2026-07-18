"""KOS search platform — enterprise search with filters."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeFile, KnowledgeTag
from app.knowledge_os.retrieval import cross_collection_search, enterprise_retrieve


def enterprise_search(
    db: Session,
    *,
    workspace_id: int,
    query: str = "",
    collection_id: int | None = None,
    collection_ids: list[int] | None = None,
    folder_id: str | None = None,
    owner_id: int | None = None,
    classification: str | None = None,
    document_type: str | None = None,
    tag: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Hybrid enterprise search with metadata filters."""
    results: dict[str, Any] = {
        "query": query,
        "chunks": [],
        "collections": [],
        "documents": [],
        "total_chunks": 0,
    }

    if query.strip():
        if collection_id:
            ret = enterprise_retrieve(
                db,
                workspace_id=workspace_id,
                query=query,
                knowledge_id=collection_id,
                limit=limit,
            )
            results["chunks"] = ret.get("hits") or []
            results["total_chunks"] = len(results["chunks"])
            results["method"] = ret.get("method")
            results["latency_ms"] = ret.get("latency_ms")
        else:
            ids = collection_ids
            if tag:
                tag_rows = (
                    db.query(KnowledgeTag)
                    .filter(KnowledgeTag.workspace_id == workspace_id, KnowledgeTag.label == tag.lower())
                    .all()
                )
                ids = list({t.knowledge_id for t in tag_rows if t.knowledge_id})
            chunks = cross_collection_search(
                db,
                workspace_id=workspace_id,
                query=query,
                collection_ids=ids,
                limit=limit,
            )
            results["chunks"] = chunks
            results["total_chunks"] = len(chunks)
            results["method"] = "cross_collection"

    # Collection metadata search
    cq = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id)
    if hasattr(KnowledgeBase, "deleted_at"):
        cq = cq.filter(KnowledgeBase.deleted_at.is_(None))
    if query and not collection_id:
        cq = cq.filter(KnowledgeBase.name.contains(query) | KnowledgeBase.description.contains(query))
    if classification and hasattr(KnowledgeBase, "classification"):
        cq = cq.filter(KnowledgeBase.classification == classification)
    if owner_id and hasattr(KnowledgeBase, "owner_id"):
        cq = cq.filter(KnowledgeBase.owner_id == owner_id)
    if date_from and hasattr(KnowledgeBase, "create_time"):
        cq = cq.filter(KnowledgeBase.create_time >= datetime.fromisoformat(date_from))
    if date_to and hasattr(KnowledgeBase, "create_time"):
        cq = cq.filter(KnowledgeBase.create_time <= datetime.fromisoformat(date_to))
    results["collections"] = [
        {"id": kb.id, "name": kb.name, "description": kb.description}
        for kb in cq.order_by(KnowledgeBase.update_time.desc()).limit(limit).all()
    ]

    # Document metadata search
    if collection_id or query:
        dq = db.query(KnowledgeFile)
        if collection_id:
            dq = dq.filter(KnowledgeFile.knowledge_id == collection_id)
        if folder_id and hasattr(KnowledgeFile, "folder_id"):
            dq = dq.filter(KnowledgeFile.folder_id == folder_id)
        if document_type and hasattr(KnowledgeFile, "document_type"):
            dq = dq.filter(KnowledgeFile.document_type == document_type)
        if classification and hasattr(KnowledgeFile, "classification"):
            dq = dq.filter(KnowledgeFile.classification == classification)
        if query:
            dq = dq.filter(KnowledgeFile.file_name.contains(query))
        results["documents"] = [
            {"id": f.id, "file_name": f.file_name, "knowledge_id": f.knowledge_id, "status": f.status}
            for f in dq.order_by(KnowledgeFile.update_time.desc()).limit(limit).all()
        ]

    return results
