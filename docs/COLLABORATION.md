# Collaboration

Location: `backend/app/conversation/collaboration.py`

## Sharing

| Feature | Support |
|---------|---------|
| Share links | Token-based with expiry |
| Read-only sharing | Default permission |
| Workspace sharing | Via visibility field |
| Public links | `GET /conversations/shared/{token}` |

## API

`POST /conversations/{id}/share` — returns `share_token`, `expires_at`

## Permissions

Share creation requires workspace editor. Shared access resolves via token without auth (read-only).

## Future

Mentions, comments, approvals via `message_type=comment|approval`.
