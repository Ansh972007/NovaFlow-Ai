# Ingestion Engine

Location: `backend/app/knowledge_os/ingestion.py`

## Pipelines

| Method | Function |
|--------|----------|
| Manual upload | `ingest_uploaded_file()` |
| URL ingest | `ingest_url_content()` |
| Sync jobs | `create_sync_job()` + `run_sync_job()` |

## Flow

```
Upload/URL/Sync → parse_document() → create_document_version() → index_document()
```

## Connectors

Registered in `knowledge_os/plugins/`:

- `manual` — process queued files
- `s3` — S3 bucket sync (stub, requires credentials)
- `git` — repository sync (stub)
- `webhook` — incremental webhook trigger

## API

- `POST /kos/collections/{id}/upload`
- `POST /kos/collections/{id}/sync`
- `POST /kos/sync/{job_id}/run`
- `GET /kos/connectors`

## Future connectors

Google Drive, OneDrive, SharePoint, Dropbox, Azure Blob, email inbox — register via `register_connector()`.
