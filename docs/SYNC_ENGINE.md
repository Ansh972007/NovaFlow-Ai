# Sync Engine

Location: `backend/app/connectivity/sync.py`

## Modes

| Mode | Description |
|------|-------------|
| `incremental` | Delta sync with checkpoint |
| `full` | Full re-sync |
| `webhook` | Event-driven sync |

## Directions

`inbound`, `outbound`, `bidirectional`

## API

`POST /connectivity/connections/{id}/sync`

## Checkpointing

Checkpoints stored in `connector_sync_jobs.checkpoint_json` for resume/rollback.
