from datetime import datetime, timezone


def estimate_cost_usd(model: str, prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    """Rough display-only estimate for common OpenAI / OpenRouter / Anthropic model ids."""
    if prompt_tokens is None and completion_tokens is None:
        return None
    mid = (model or "").lower()
    # prompt / completion per 1M tokens
    table = {
        "gpt-4o-mini": (0.15, 0.60),
        "openai/gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.0),
        "openai/gpt-4o": (2.50, 10.0),
        "gpt-4.1-mini": (0.40, 1.60),
        "gpt-4.1": (2.00, 8.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "claude-3-5-haiku": (0.80, 4.00),
        "claude-3-5-sonnet": (3.00, 15.0),
        "claude-3-haiku": (0.25, 1.25),
        "claude-sonnet-4": (3.00, 15.0),
        "claude-opus": (15.0, 75.0),
        "gemini-2.0-flash": (0.10, 0.40),
        "gemini-flash": (0.10, 0.40),
        "llama-3.1-70b": (0.59, 0.79),
        "llama-3.3-70b": (0.59, 0.79),
        "deepseek-chat": (0.14, 0.28),
        "deepseek-r1": (0.55, 2.19),
        "qwen": (0.15, 0.60),
        "mistral": (0.20, 0.60),
    }
    rates = None
    for key, val in table.items():
        if key in mid:
            rates = val
            break
    if not rates:
        rates = (0.15, 0.60)
    p, c = rates
    pt = int(prompt_tokens or 0)
    ct = int(completion_tokens or 0)
    return round((pt * p + ct * c) / 1_000_000, 6)


def build_chat_receipt(
    *,
    model: str,
    rag_hits: list[dict] | None = None,
    ab_meta: dict | None = None,
    chars: int = 0,
    event_type: str = "chat",
    usage: dict | None = None,
    stopped: bool = False,
) -> dict:
    hits = rag_hits or []

    # One chip per retrieved chunk so [n] aligns with RAG context numbering
    chunks = []
    for i, hit in enumerate(hits[:8], start=1):
        text = (hit.get("text") or "").strip()
        chunks.append(
            {
                "n": i,
                "file_name": hit.get("file_name") or "document",
                "score": hit.get("score"),
                "rrf": hit.get("rrf"),
                "method": hit.get("method"),
                "preview": text[:240] + ("…" if len(text) > 240 else ""),
            }
        )

    sources = []
    seen = set()
    for c in chunks:
        name = c["file_name"]
        if name not in seen:
            seen.add(name)
            sources.append(name)

    prompt_tokens = (usage or {}).get("prompt_tokens")
    completion_tokens = (usage or {}).get("completion_tokens")
    total_tokens = (usage or {}).get("total_tokens")
    if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
        total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)

    resolved_model = model or (usage or {}).get("model") or "default"

    receipt = {
        "version": 2,
        "event_type": event_type,
        "model": resolved_model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chars": chars,
        "rag_used": bool(hits),
        "retrieval_method": next((h.get("method") for h in hits if h.get("method")), None),
        "source_count": len(sources),
        "sources": sources,
        "chunks": chunks,
        "stopped": bool(stopped),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "est_cost_usd": estimate_cost_usd(resolved_model, prompt_tokens, completion_tokens),
    }
    if ab_meta:
        receipt["ab_variant"] = ab_meta.get("variant")
        receipt["ab_model"] = ab_meta.get("model")
        receipt["ab_route_id"] = ab_meta.get("route_id")
    return receipt
