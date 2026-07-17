# Knowledge Runtime

Location: `backend/app/runtime/knowledge.py`

Wraps existing hybrid search in `app/services/knowledge.py` with tenant boundaries and caching.

## Retrieval methods

- **Vector search** — embeddings + Milvus/pgvector/Qdrant
- **Keyword search** — SQL `LIKE` token search
- **Hybrid** — RRF fusion of vector + keyword
- **Metadata** — file name boost, chunk ranking

## Tenant awareness

- Assistant path: validates `assistant.workspace_id == ctx.workspace_id`
- Knowledge base path: validates `knowledge_base.workspace_id == ctx.workspace_id`
- Wrong workspace → empty `KnowledgeBundle`

## Cache

Tenant-scoped knowledge cache (120s TTL) via `runtime/cache.py`:

- Key: `rag:{assistant_id}:{query_hash}` or `kb:{id}:{query_hash}`
- Tags: `assistant:{id}`, `kb:{id}`, `ws:{workspace_id}`

## Citations

Hits are formatted as `[n] (filename)\ntext` for prompt compiler and UI receipts.

## Usage

```python
from app.runtime.knowledge import resolve_assistant_knowledge, resolve_knowledge_base

kb = resolve_assistant_knowledge(ctx, assistant_id, query)
# kb.context, kb.hits, kb.method, kb.cache_hit
```

## Permissions

Knowledge retrieval for tools requires `Permission.KNOWLEDGE_READ` (enforced in tool runtime).
