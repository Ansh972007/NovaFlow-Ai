# Threading Engine

Location: `backend/app/conversation/threading.py`

## Features

| Feature | API |
|---------|-----|
| Unlimited threads | Auto-created main thread per conversation |
| Fork conversation | `POST /conversations/{id}/fork` |
| Merge branch | `POST /conversations/branches/{id}/merge` |
| Pin | `pin_conversation()` |
| Archive | `POST /conversations/{id}/archive` |
| Restore | `POST /conversations/{id}/restore` |
| Snapshot | `POST /conversations/{id}/snapshot` |

## Branch model

Fork creates a new `Conversation` linked via `ConversationBranch`. Parent message ID preserved for context restoration.

## Nested replies

Set `parent_message_id` when creating messages via API.
