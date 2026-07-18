# Plugin SDK

Location: `backend/app/workflow_intelligence/plugin_sdk.py`

## Registry

```python
from app.workflow_intelligence.plugin_sdk import plugin_registry, PluginManifest

async def my_custom_node(db, context, data, **kwargs):
    return {"output": "done", "status": "ok"}

plugin_registry.register_node(
    "my_custom",
    my_custom_node,
    manifest=PluginManifest("acme.nodes", "Acme Nodes", node_types=["my_custom"]),
)

plugin_registry.register_validator(lambda graph: [])
```

## Extensibility surface

| Hook | Purpose |
|------|---------|
| Custom nodes | New `node.type` handlers |
| Custom validators | Pre-publish checks |
| Manifests | Plugin discovery |

## Requirements

Custom handlers must:
- Respect tenant scope (`workspace_id`)
- Not bypass PlatformContext when invoked from routers
- Use AI Runtime for LLM operations

## Future

Custom triggers, actions, auth providers register via same registry; engine dispatches unknown types to registry before failing.

---

# Knowledge OS Plugins

Location: `backend/app/knowledge_os/plugins/`

## Connectors

```python
from app.knowledge_os.plugins import register_connector, BaseConnector, ConnectorResult

class AcmeDriveConnector(BaseConnector):
    connector_type = "acme_drive"
    description = "Acme Drive sync"

    def sync(self, db, job):
        return ConnectorResult(imported=3).to_dict()

register_connector("acme_drive", AcmeDriveConnector)
```

## Built-in connectors

| Type | Description |
|------|-------------|
| `manual` | Process queued uploads |
| `s3` | S3 bucket sync stub |
| `git` | Git repo sync stub |
| `webhook` | Webhook-triggered incremental |

## Extensibility surface

| Hook | Purpose |
|------|---------|
| Connectors | Remote source sync |
| Parsers | Custom `parse_document` extensions |
| Chunkers | Custom chunk strategies |
| Rerankers | Post-retrieval ranking |
| Entity extractors | Graph enrichment |

## Requirements

Plugins must:
- Respect tenant scope (`workspace_id`)
- Not bypass PlatformContext
- Route AI operations through AI Runtime
- Use `index_document()` for embedding — not direct chunk writes
