# Connector SDK

Location: `backend/app/connectivity/sdk/client.py`

## Python SDK

```python
from app.connectivity.sdk.client import ConnectivityClient

client = ConnectivityClient("https://api.example.com", token="...", workspace_id=1)
connectors = await client.list_connectors()
result = await client.invoke_action("conn_id", "notify", {"message": "Hello"})
```

## REST API

All endpoints under `/api/v1/connectivity/*`

## CLI

Use standard HTTP clients against REST API; dedicated CLI planned for connector certification workflow.
