# Security Model (Knowledge OS)

Location: `backend/app/knowledge_os/security.py`

## Classification levels

`public` → `internal` → `confidential` → `restricted` → `secret`

Access requires user max classification ≥ resource classification.

## Scanning

`scan_document_content()` detects:

- PII (SSN, credit card, email patterns)
- Prompt injection signals

## Tenant isolation

Every query filtered by `workspace_id` from PlatformContext. Cross-workspace retrieval blocked in `enterprise_retrieve()`.

## Encryption

Documents stored on object storage / local upload dir. Encrypted-at-rest via Data Platform object storage config.

## Audit

Collection create/upload/archive logged via `ctx.audit()`. Retrieval emits `KnowledgeRetrieved` platform event.

## API

- `POST /kos/scan` — content compliance scan

## Legal hold

Collection `legal_hold` blocks archive (via `archive_collection()`).
