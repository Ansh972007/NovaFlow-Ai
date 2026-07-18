# Knowledge Graph

Location: `backend/app/knowledge_os/graph.py`

## Entity types

Rule-based extraction for: email, project, product, contract, invoice.

## Functions

| Function | Purpose |
|----------|---------|
| `extract_entities_from_text()` | Create entity nodes |
| `build_graph_for_file()` | Entities + co-occurrence relationships |
| `search_entities()` | Entity search |
| `get_entity_graph()` | Visual graph (nodes + edges) |

## Relationships

Default `co_occurs` edges between entities in same document chunk window.

## API

- `GET /kos/graph/entities`
- `GET /kos/graph/entities/{id}`
- `POST /kos/documents/{id}/build-graph`

## Extension

Replace rule patterns with LLM extraction via AI Runtime plugin — register in `knowledge_os/plugins/`.
