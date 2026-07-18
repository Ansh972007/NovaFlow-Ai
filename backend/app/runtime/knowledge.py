"""Knowledge runtime — tenant-aware hybrid retrieval with citations."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    """Retrieve knowledge linked to an assistant via Enterprise KOS."""
    from app.database import Assistant
    from app.knowledge_os.integration import retrieve_for_runtime

    assistant = ctx.db.get(Assistant, assistant_id)
    if not assistant or assistant.workspace_id != ctx.workspace_id:
        return KnowledgeBundle()

    return retrieve_for_runtime(ctx, query, assistant_id=assistant_id, limit=limit)


def resolve_knowledge_base(
    ctx: RuntimeContext,
    knowledge_id: int,
    query: str,
    *,
    limit: int = 5,
) -> KnowledgeBundle:
    """Retrieve from a single collection via Enterprise KOS."""
    from app.database import KnowledgeBase
    from app.knowledge_os.integration import retrieve_for_runtime

    kb = ctx.db.get(KnowledgeBase, knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return KnowledgeBundle()

    return retrieve_for_runtime(ctx, query, knowledge_id=knowledge_id, limit=limit)
