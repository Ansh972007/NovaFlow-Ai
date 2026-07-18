# Plugin Guide

Location: `backend/app/connectivity/plugins/`

## Build a custom connector

```python
from app.connectivity.plugins.base import BaseConnectorPlugin, PluginResult
from app.connectivity.plugins import register_connector_plugin

class AcmeCRMPlugin(BaseConnectorPlugin):
    connector_type = "acme_crm"
    description = "Acme CRM integration"

    def test(self, db, conn, secret=""):
        return PluginResult(success=bool(secret))

    def invoke_action(self, db, conn, action, params=None, secret=""):
        if action == "create_lead":
            return PluginResult(success=True, data={"lead_id": "123"})
        return PluginResult(success=False, message="Unknown action")

register_connector_plugin("acme_crm", AcmeCRMPlugin)
```

## Requirements

- Respect `workspace_id` tenant scope
- Never bypass PlatformContext
- Route AI operations through AI Runtime
- Log events via `connectivity/events.log_event`
- Encrypt secrets via `connectivity/secrets`

## Certification

Test via `POST /connectivity/connections/{id}/test` before publishing.
