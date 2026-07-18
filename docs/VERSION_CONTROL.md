# Version Control

Location: `backend/app/knowledge_os/versioning.py`

## Capabilities

| Function | Purpose |
|----------|---------|
| `create_document_version()` | Snapshot on upload/change |
| `list_versions()` | Version history |
| `compare_versions()` | Unified diff + metadata diff |
| `restore_version()` | Rollback to prior version |

## Automatic versioning

Triggered on:

- File upload (`router.py`)
- URL ingest (`ingestion.py`)
- Version restore

## Fields

- `version_no`, `content_hash`, `change_summary`, `approval_status`, `created_by`

## API

- `GET /kos/documents/{id}/versions`
- `POST /kos/versions/compare`
- `POST /kos/documents/{id}/restore-version`

## Document lifecycle

`lifecycle_status`: draft, published, archived, deleted (via collection archive + retention).
