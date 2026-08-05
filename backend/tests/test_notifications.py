"""Notifications automated test suite."""

from __future__ import annotations

import json
import os
import tempfile
import asyncio
from pathlib import Path

# Isolate tests from the developer's local SQLite so we never mutate production-ish data.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-notifications-test-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-test-secret"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
from tests.conftest import TEST_ADMIN_PASSWORD
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal, Notification, UserNotificationPreference, WorkspaceMember, User
from app.platform_intelligence.events.emitter import emit_platform_event
from tests.test_smoke import _auth_headers


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_notifications_crud_and_preferences(client):
    headers = _auth_headers(client)
    token = headers["Authorization"].split(" ")[1]

    # Resolve active workspace
    db = SessionLocal()
    try:
        member = db.query(WorkspaceMember).first()
        assert member is not None, "Workspace seed should have created a default workspace membership"
        workspace_id = member.workspace_id
        user_id = member.user_id
    finally:
        db.close()

    # 1. Verify User Preferences Endpoint
    resp = client.get("/api/v1/notifications/preferences", headers=headers)
    assert resp.status_code == 200
    pref_data = resp.json()["data"]
    assert "muted_categories" in pref_data
    assert "enabled_channels" in pref_data

    # 2. Patch Preferences (Mute the "KNOWLEDGE" category)
    patch_resp = client.patch(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={"muted_categories": ["KNOWLEDGE"], "do_not_disturb": 1},
    )
    assert patch_resp.status_code == 200
    updated_pref = patch_resp.json()["data"]
    assert "KNOWLEDGE" in updated_pref["muted_categories"]
    assert updated_pref["do_not_disturb"] == 1

    # 3. Emit WorkflowStarted platform event to trigger template notification
    emit_platform_event(
        None, # db bypass so it only invokes handler in-memory subscription loop
        "WorkflowStarted",
        workspace_id=workspace_id,
        actor_user_id=user_id,
        resource_type="workflow",
        resource_id="wf_test_123",
        payload={"workflow_name": "Compliance Core Check"},
    )

    # Allow async task loop a microsecond to process the handler
    import time
    time.sleep(0.5)

    # 4. Fetch notifications to verify it was written to the DB
    list_resp = client.get(f"/api/v1/notifications?workspace_id={workspace_id}", headers=headers)
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    assert data["total"] > 0
    first_notif = data["rows"][0]
    assert first_notif["title"] == "Workflow Started"
    assert "Compliance Core Check" in first_notif["message"]
    assert first_notif["category"] == "WORKFLOW"
    assert first_notif["is_read"] == 0

    # 5. Get unread count
    count_resp = client.get(f"/api/v1/notifications/unread-count?workspace_id={workspace_id}", headers=headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["data"]["unread_count"] > 0

    # 6. Mark read
    notif_id = first_notif["id"]
    read_resp = client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["data"]["is_read"] == 1

    # 7. Verify unread count decremented
    count_resp2 = client.get(f"/api/v1/notifications/unread-count?workspace_id={workspace_id}", headers=headers)
    assert count_resp2.status_code == 200
    assert count_resp2.json()["data"]["unread_count"] == 0

    # 8. Delete notification
    del_resp = client.delete(f"/api/v1/notifications/{notif_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] == notif_id


def test_notifications_websocket_handshake(client):
    headers = _auth_headers(client)
    token = headers["Authorization"].split(" ")[1]

    # Resolve active workspace
    db = SessionLocal()
    try:
        member = db.query(WorkspaceMember).first()
        workspace_id = member.workspace_id
    finally:
        db.close()

    # Verify WS connection parameters
    with client.websocket_connect(f"/api/v1/notifications/ws?token={token}&workspace_id={workspace_id}") as ws:
        # Re-emit in background or send dummy message to keep loop active
        ws.send_text("ping")
        # Connection succeeds without throwing WebSocketDisconnect immediately
