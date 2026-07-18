"""KOS retrieval engine — BM25, dense, hybrid, cross-collection."""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.database import AssistantKnowledge, KnowledgeBase
from app.services.knowledge import rag_hits_for_assistant, search_chunks_semantic


def _expand_query(query: str) -> list[str]:
    """Light query expansion — original + keyword variants."""
    q = query.strip()
    if not q:
        return []
    variants = [q]
    tokens = re.findall(r"[a-z0-9]+", q.lower())
    if len(tokens) >= 2:
        variants.append(" ".join(tokens[:3]))
    return list(dict.fromkeys(variants))


def _rerank_hits(hits: list[dict], query: str) -> list[dict]:
    """Filename and RRF score reranking."""
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    for hit in hits:
        boost = 0.0
        name = (hit.get("file_name") or "").lower()
        if q_tokens and any(t in name for t in q_tokens if len(t) > 3):
            boost += 0.08
        if hit.get("classification") == "restricted":
            boost -= 0.05
        hit["score"] = round(float(hit.get("score") or hit.get("rrf") or 0) + boost, 4)
    hits.sort(key=lambda h: (-(h.get("rrf") or 0), -(h.get("score") or 0)))
    return hits


def enterprise_retrieve(
    db: Session,
    *,
    workspace_id: int,
    query: str,
    knowledge_id: int | None = None,
    assistant_id: str | None = None,
    limit: int = 5,
    classification_max: str = "restricted",
    trace_id: str = "",
) -> dict[str, Any]:
    """
    Single entry point for all platform retrieval.
    Never call search_chunks_semantic directly from feature code.
    """
    start = time.perf_counter()
    hits: list[dict] = []
    method = "none"

    if assistant_id:
        hits = rag_hits_for_assistant(db, assistant_id, query, limit)
        method = hits[0].get("method") if hits else "none"
    elif knowledge_id:
        kb = db.get(KnowledgeBase, knowledge_id)
        if not kb or kb.workspace_id != workspace_id:
            return _empty_result(start, trace_id)
        if getattr(kb, "deleted_at", None) or getattr(kb, "status", "") == "archived":
            return _empty_result(start, trace_id)
        # Multi-query retrieval
        all_lists: list[list[dict]] = []
        for variant in _expand_query(query)[:2]:
            all_lists.append(search_chunks_semantic(db, knowledge_id, variant, limit * 2))
        if len(all_lists) > 1:
            from app.services.knowledge import _rrf_fuse

            hits = _rrf_fuse(all_lists, limit)
            method = "hybrid"
        else:
            hits = all_lists[0][:limit] if all_lists else []
            method = hits[0].get("method") if hits else "none"
    else:
        return _empty_result(start, trace_id)

    hits = _rerank_hits(hits, query)[:limit]
    for h in hits:
        h["knowledge_id"] = knowledge_id or h.get("knowledge_id")
        h["trace_id"] = trace_id

    context_parts = []
    for i, hit in enumerate(hits, 1):
        source = hit.get("file_name") or "document"
        text = (hit.get("text") or "")[:1200]
        context_parts.append(f"[{i}] ({source})\n{text}")

    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "hits": hits,
        "context": "\n\n".join(context_parts),
        "method": method,
        "hit_count": len(hits),
        "latency_ms": latency_ms,
        "trace_id": trace_id,
    }


def cross_collection_search(
    db: Session,
    *,
    workspace_id: int,
    query: str,
    collection_ids: list[int] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Permission-aware search across multiple collections in a workspace."""
    q = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id)
    if hasattr(KnowledgeBase, "deleted_at"):
        q = q.filter(KnowledgeBase.deleted_at.is_(None))
    if collection_ids:
        q = q.filter(KnowledgeBase.id.in_(collection_ids))
    collections = q.all()
    merged: list[dict] = []
    per_col = max(3, limit // max(len(collections), 1))
    for kb in collections:
        result = enterprise_retrieve(
            db,
            workspace_id=workspace_id,
            query=query,
            knowledge_id=kb.id,
            limit=per_col,
        )
        for hit in result.get("hits") or []:
            hit["collection_name"] = kb.name
            hit["collection_id"] = kb.id
            merged.append(hit)
    merged.sort(key=lambda h: (-(h.get("rrf") or 0), -(h.get("score") or 0)))
    return merged[:limit]


def resolve_assistant_collection_ids(db: Session, assistant_id: str) -> list[int]:
    rows = db.query(AssistantKnowledge).filter(AssistantKnowledge.assistant_id == assistant_id).all()
    return [r.knowledge_id for r in rows]


def _empty_result(start: float, trace_id: str) -> dict[str, Any]:
    return {
        "hits": [],
        "context": "",
        "method": "none",
        "hit_count": 0,
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "trace_id": trace_id,
    }
