"""KOS integration — single retrieval path for runtime, agents, workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_os.retrieval import enterprise_retrieve


def retrieve_for_runtime(
    ctx,
    query: str,
    *,
    knowledge_id: int | None = None,
    assistant_id: str | None = None,
    limit: int = 5,
):
    """Tenant-aware retrieval through KOS — all feature code should use this."""
    from app.runtime.cache import runtime_cache_get, runtime_cache_set
    from app.runtime.knowledge import KnowledgeBundle, _dict_hits

    if not query.strip():
        return KnowledgeBundle()

    cache_key = f"kos:{assistant_id or ''}:{knowledge_id or ''}:{hash(query.strip().lower())}:{limit}"
    cached = runtime_cache_get(ctx.workspace_id, "knowledge", cache_key)
    if cached:
        hits_raw = cached.get("hits") or []
        return KnowledgeBundle(
            context=cached.get("context") or "",
            hits=_dict_hits(hits_raw),
            method=cached.get("method") or "hybrid",
            cache_hit=True,
        )

    trace_id = getattr(ctx, "trace_id", "") or ""
    result = enterprise_retrieve(
        ctx.db,
        workspace_id=ctx.workspace_id,
        query=query,
        knowledge_id=knowledge_id,
        assistant_id=assistant_id,
        limit=limit,
        trace_id=trace_id,
    )

    hits_raw = result.get("hits") or []
    runtime_cache_set(
        ctx.workspace_id,
        "knowledge",
        cache_key,
        {"hits": hits_raw, "context": result.get("context") or "", "method": result.get("method")},
        ttl_seconds=120,
        tags=[f"kb:{knowledge_id}"] if knowledge_id else [f"assistant:{assistant_id}"],
    )

    try:
        from app.platform_intelligence.events.emitter import emit_platform_event

        emit_platform_event(
            ctx.db,
            "KnowledgeRetrieved",
            workspace_id=ctx.workspace_id,
            organization_id=getattr(ctx, "organization_id", None),
            actor_user_id=getattr(ctx, "user_id", None),
            resource_type="knowledge",
            resource_id=str(knowledge_id or assistant_id or ""),
            payload={
                "hit_count": result.get("hit_count", 0),
                "method": result.get("method"),
                "latency_ms": result.get("latency_ms"),
                "trace_id": trace_id,
            },
        )
    except Exception:
        pass

    return KnowledgeBundle(
        context=result.get("context") or "",
        hits=_dict_hits(hits_raw),
        method=result.get("method") or "hybrid",
    )


def retrieve_for_agent(
    db: Session,
    *,
    workspace_id: int,
    query: str,
    knowledge_id: int | None = None,
    assistant_id: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    return enterprise_retrieve(
        db,
        workspace_id=workspace_id,
        query=query,
        knowledge_id=knowledge_id,
        assistant_id=assistant_id,
        limit=limit,
    )


def format_hits_for_tool(hits: list[dict]) -> str:
    if not hits:
        return "(no knowledge matches)"
    lines = []
    for i, h in enumerate(hits, 1):
        src = h.get("file_name") or "document"
        text = (h.get("text") or "").strip()[:400]
        method = h.get("method") or ""
        tag = f" [{method}]" if method else ""
        lines.append(f"[{i}] {src}{tag}: {text}")
    return "\n".join(lines)
