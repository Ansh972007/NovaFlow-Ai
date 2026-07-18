# Indexing Engine

Location: `backend/app/knowledge_os/indexing.py`

## Functions

| Function | Purpose |
|----------|---------|
| `index_document()` | Full parse → chunk → embed pipeline |
| `reindex_collection()` | Full or partial reindex |
| `detect_duplicates()` | Content-hash duplicate detection |

## Pipeline

Delegates core embedding to `services/knowledge.process_file_record()` then stamps KOS metadata:

- `content_hash` on chunks
- `version_no` alignment with document version

## Incremental indexing

Upload sets `status=5` (queued). Index transitions through processing → ready/failed.

## API

- `POST /kos/collections/{id}/reindex`

## Vector backends

Embeddings stored in `knowledge_chunks.embedding_json` and external vector store via `app/data/vectors/`.
