import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_smoke import client, _auth_headers


def test_capabilities_list(client):
    headers = _auth_headers(client)
    res = client.get("/api/v1/aios/capabilities", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status_code"] == 200
    
    caps = body["data"]
    assert len(caps) >= 5
    ids = {c["id"] for c in caps}
    assert "cap_voice" in ids
    assert "cap_ocr" in ids


def test_project_goal_compile_and_status(client):
    headers = _auth_headers(client)
    # Submit goal
    res = client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "I need a restaurant telegram bot to store menus in database"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status_code"] == 200
    
    data = body["data"]
    assert data["project_id"] is not None
    assert data["solution_id"] is not None
    assert data["status"] == "compiled_draft"
    # Gap analysis checks should flag telegram bot token because it's missing by default
    assert "telegram_bot_token" in data["missing_credentials"]
    
    # Query status
    status_res = client.get(f"/api/v1/aios/project/{data['project_id']}", headers=headers)
    assert status_res.status_code == 200
    status_body = status_res.json()
    assert status_body["status_code"] == 200
    
    status_data = status_body["data"]
    assert status_data["project_id"] == data["project_id"]
    assert status_data["status"] == "compiled_draft"
    assert status_data["solution_status"] == "compiled_draft"
    assert "db_orders" in status_data["graph"]["nodes"]


def test_component_reuse_matching(client):
    headers = _auth_headers(client)
    # Submit a goal matching built-in templates (e.g. "rag" or "support")
    res = client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "Process customer support workflow queries"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status_code"] == 200
    
    data = body["data"]
    assert data["status"] == "reused"
    assert data["solution_id"] == "support"
