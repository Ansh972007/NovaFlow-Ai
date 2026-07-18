# Retrieval Engine

Location: `backend/app/knowledge_os/retrieval.py`

## Entry point

```python
from app.knowledge_os import enterprise_retrieve

result = enterprise_retrieve(db, workspace_id=1, query="...", knowledge_id=42, limit=5)
```

## Methods

| Method | Description |
|--------|-------------|
| BM25 | Keyword token search via `_token_search` |
| Dense | Vector cosine / Milvus ANN |
| Hybrid | RRF fusion of vector + keyword |
| Multi-query | Query expansion + fusion |
| Reranking | Filename boost + classification penalty |

## Cross-collection

`cross_collection_search()` — permission-aware workspace search across collections.

## Runtime integration

`integration.retrieve_for_runtime()` wraps retrieval with caching and Platform Intelligence events (`KnowledgeRetrieved`).

## API

- `POST /kos/retrieve`
- `POST /kos/search`

## Rule

Feature code must not call `search_chunks_semantic` directly. Use KOS retrieval.
