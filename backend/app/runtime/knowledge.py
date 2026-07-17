"""Knowledge runtime — tenant-aware hybrid retrieval with citations."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.runtime.cache import runtime_cache_get, runtime_cache_set
from app.runtime.context import RuntimeContext


@dataclass
class KnowledgeHit:
    text: str
    file_name: str = ""
    score: float | None = None
    method: str = ""
    knowledge_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "file_name": self.file_name,
            "score": self.score,
            "method": self.method,
            "knowledge_id": self.knowledge_id,
        }


@dataclass
class KnowledgeBundle:
    context: str = ""
    hits: list[KnowledgeHit] = field(default_factory=list)
    method: str = "none"
    cache_hit: bool = False

    @property
    def hit_count(self) -> int:
        return len(self.hits)


def _hits_to_context(hits: list[dict]) -> str:
    if not hits:
        return ""
    parts = []
    for i, hit in enumerate(hits, 1):
        source = hit.get("file_name") or "document"
        text = (hit.get("text") or "")[:1200]
        parts.append(f"[{i}] ({source})\n{text}")
    return "\n\n".join(parts)


def _dict_hits(raw: list[dict]) -> list[KnowledgeHit]:
    out: list[KnowledgeHit] = []
    for h in raw:
        out.append(
            KnowledgeHit(
                text=(h.get("text") or "")[:1200],
                file_name=h.get("file_name") or "",
                score=h.get("score"),
                method=h.get("method") or "",
                knowledge_id=h.get("knowledge_id"),
            )
        )
    return out


def resolve_assistant_knowledge(
    ctx: RuntimeContext,
    assistant_id: str,
    query: str,
    *,
    limit: int = 5,
) -> KnowledgeBundle:
    """Retrieve knowledge linked to an assistant (tenant-scoped via assistant workspace)."""
    from app.database import Assistant
    from app.services.knowledge import rag_context_for_assistant, rag_hits_for_assistant

    assistant = ctx.db.get(Assistant, assistant_id)
    if not assistant or assistant.workspace_id != ctx.workspace_id:
        return KnowledgeBundle()

    cache_key = f"rag:{assistant_id}:{hash(query.strip().lower())}:{limit}"
    cached = runtime_cache_get(ctx.workspace_id, "knowledge", cache_key)
    if cached:
        hits_raw = cached.get("hits") or []
        return KnowledgeBundle(
            context=cached.get("context") or "",
            hits=_dict_hits(hits_raw),
            method=cached.get("method") or "hybrid",
            cache_hit=True,
        )

    hits_raw = rag_hits_for_assistant(ctx.db, assistant_id, query, limit)
    context = rag_context_for_assistant(ctx.db, assistant_id, query, limit)
    method = hits_raw[0].get("method") if hits_raw else "none"

    runtime_cache_set(
        ctx.workspace_id,
        "knowledge",
        cache_key,
        {"hits": hits_raw, "context": context, "method": method},
        ttl_seconds=120,
        tags=[f"assistant:{assistant_id}"],
    )
    return KnowledgeBundle(context=context, hits=_dict_hits(hits_raw), method=method or "hybrid")


def resolve_knowledge_base(
    ctx: RuntimeContext,
    knowledge_id: int,
    query: str,
    *,
    limit: int = 5,
) -> KnowledgeBundle:
    """Retrieve from a single knowledge base with workspace validation."""
    from app.database import KnowledgeBase
    from app.services.knowledge import search_chunks_semantic

    kb = ctx.db.get(KnowledgeBase, knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return KnowledgeBundle()

    cache_key = f"kb:{knowledge_id}:{hash(query.strip().lower())}:{limit}"
    cached = runtime_cache_get(ctx.workspace_id, "knowledge", cache_key)
    if cached:
        hits_raw = cached.get("hits") or []
        return KnowledgeBundle(
            context=cached.get("context") or "",
            hits=_dict_hits(hits_raw),
            method=cached.get("method") or "hybrid",
            cache_hit=True,
        )

    hits_raw = search_chunks_semantic(ctx.db, knowledge_id, query, limit)
    context = _hits_to_context(hits_raw)
    method = hits_raw[0].get("method") if hits_raw else "none"

    runtime_cache_set(
        ctx.workspace_id,
        "knowledge",
        cache_key,
        {"hits": hits_raw, "context": context, "method": method},
        ttl_seconds=120,
        tags=[f"kb:{knowledge_id}"],
    )
    return KnowledgeBundle(context=context, hits=_dict_hits(hits_raw), method=method or "hybrid")
