# Search Platform

Location: `backend/app/knowledge_os/search.py`

## `enterprise_search()`

Hybrid enterprise search with metadata filters:

| Filter | Field |
|--------|-------|
| Collection | `collection_id`, `collection_ids` |
| Folder | `folder_id` |
| Owner | `owner_id` |
| Classification | `classification` |
| Document type | `document_type` |
| Tag | `tag` |
| Date range | `date_from`, `date_to` |

## Result sections

- `chunks` — semantic/hybrid retrieval hits
- `collections` — metadata matches
- `documents` — file name matches

## Cross-workspace

Not supported — all queries scoped to `workspace_id` from PlatformContext.

## API

`POST /kos/search`

## Analytics

`GET /kos/analytics` — workspace-level collection/document/chunk stats.
