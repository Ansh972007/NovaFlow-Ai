# Event Engine

Location: `backend/app/connectivity/events.py`

## Capabilities

- Incoming/outgoing webhooks
- Event logging with trace IDs
- Outbound delivery via SSRF-safe `post_webhook`
- Event replay from `connector_events` log

## API

- `POST /connectivity/webhooks`
- `POST /connectivity/webhooks/{id}/deliver`
- `GET /connectivity/events`

## Platform events

Connector actions emit `ConnectorActionInvoked` via Platform Intelligence.
