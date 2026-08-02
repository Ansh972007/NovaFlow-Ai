import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_smoke import _auth_headers


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_kernel_status_requires_auth(client):
    """Test that unauthorized requests to the AIOS Kernel status endpoint are blocked."""
    res = client.get("/api/v1/aios/kernel/status")
    assert res.status_code in (401, 403)


def test_kernel_status_success(client):
    """Test that authenticated requests to the AIOS Kernel status endpoint return configuration attributes."""
    headers = _auth_headers(client)
    res = client.get("/api/v1/aios/kernel/status", headers=headers)
    assert res.status_code == 200
    
    body = res.json()
    assert body["status_code"] == 200
    
    data = body["data"]
    assert data["kernel_version"] == "12.2.0"
    assert data["status"] == "active"
    assert data["registered_capabilities_count"] == 22
    assert data["active_workers_count"] == 12
    assert "active_provider_id" in data
    assert "heartbeat_interval" in data
