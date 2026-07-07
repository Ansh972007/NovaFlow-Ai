from datetime import datetime, timezone


def build_chat_receipt(
    *,
    model: str,
    rag_hits: list[dict] | None = None,
    ab_meta: dict | None = None,
    chars: int = 0,
    event_type: str = "chat",
) -> dict:
    hits = rag_hits or []
    sources = []
    seen = set()
    for hit in hits:
        name = hit.get("file_name") or "document"
        if name not in seen:
            seen.add(name)
            sources.append(name)

    chunks = []
    for hit in hits[:8]:
        text = (hit.get("text") or "").strip()
        chunks.append(
            {
                "file_name": hit.get("file_name") or "document",
                "score": hit.get("score"),
                "method": hit.get("method"),
                "preview": text[:240] + ("…" if len(text) > 240 else ""),
            }
        )

    receipt = {
        "version": 1,
        "event_type": event_type,
        "model": model or "default",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chars": chars,
        "rag_used": bool(hits),
        "source_count": len(sources),
        "sources": sources,
        "chunks": chunks,
    }
    if ab_meta:
        receipt["ab_variant"] = ab_meta.get("variant")
        receipt["ab_model"] = ab_meta.get("model")
        receipt["ab_route_id"] = ab_meta.get("route_id")
    return receipt
