# Developer Platform

## SDKs

| SDK | Location | Status |
|-----|----------|--------|
| Python | `platform_intelligence/sdk/client.py` | REST client for dashboards/events |
| Plugin | `workflow_intelligence/plugin_sdk.py` | Custom workflow nodes |
| REST | Platform Intelligence API | Full HTTP surface |

## Python client

```python
from app.platform_intelligence.sdk.client import NovaFlowPlatformClient

client = NovaFlowPlatformClient("http://127.0.0.1:8000", token="...", workspace_id=1)
health = await client.health()
dashboard = await client.workspace_dashboard()
```

## CLI (future)

Wrap SDK with `click` for `novaflow health`, `novaflow events`, `novaflow dashboard`.

## JavaScript SDK (future)

Mirror Python client in `src/lib/platform/`.

## Trace propagation

Send `X-Trace-Id` header from clients; middleware propagates through all subsystems.

## API discovery

All endpoints under `/api/v1/platform/intelligence/` — see `PLATFORM_ARCHITECTURE.md`.
