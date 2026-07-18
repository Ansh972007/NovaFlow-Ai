# Knowledge Architecture

NovaFlow Enterprise Knowledge Operating System (`backend/app/knowledge_os/`) is the **permanent enterprise knowledge layer** for all AI retrieval.

## Position in stack

```
Security → Platform → Data → AI Runtime → Workflow Intelligence → Platform Intelligence → Conversation Platform → Knowledge OS
```

## Hierarchy

```
Organization → Workspace → Collections → Folders → Documents → Versions → Chunks → Embeddings → Knowledge Graph
```

## Data model

| Table | Purpose |
|-------|---------|
| `knowledge_bases` | Collections with classification, retention, tags |
| `knowledge_folders` | Nested folder hierarchy |
| `knowledge_files` | Documents with lifecycle, version, hash |
| `knowledge_chunks` | Indexed chunks with embeddings |
| `knowledge_document_versions` | Version history |
| `knowledge_entities` | Graph nodes |
| `knowledge_relationships` | Graph edges |
| `knowledge_tags` | Labels |
| `knowledge_sync_jobs` | Connector sync jobs |

## Single retrieval path

All features must use `enterprise_retrieve()` or `retrieve_for_runtime()` — never call `search_chunks_semantic` directly from feature code.

| Consumer | Integration |
|----------|-------------|
| AI Runtime | `knowledge_os/integration.py` → `retrieve_for_runtime()` |
| Agent `kb_search` tool | `retrieve_for_agent()` |
| Workflow retrieve node | Runtime bridge → KOS |
| Conversation citations | `knowledge_refs` on messages |

## API

Prefix: `/api/v1/kos/*`

Legacy `/api/v1/knowledge/*` remains for UI backward compatibility.

## Health

`"knowledge_os": "enterprise-v1"` on `/health`

See: `INGESTION_ENGINE.md`, `INDEXING_ENGINE.md`, `RETRIEVAL_ENGINE.md`, `KNOWLEDGE_GRAPH.md`, `SEARCH_PLATFORM.md`, `VERSION_CONTROL.md`, `SECURITY_MODEL.md`, `PLUGIN_SDK.md` (Knowledge OS section).
