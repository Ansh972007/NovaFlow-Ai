"""Settings-related workspace and integration API smoke tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, User, Workspace, WorkspaceMember
from tests.test_smoke import _auth_headers, client as test_client


@pytest.fixture
def auth_headers(test_client: TestClient):
    return _auth_headers(test_client)


def _workspace_id(client: TestClient, headers: dict) -> int:
    res = client.get("/api/v1/workspaces", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    wid = data.get("current_id") or (data.get("items") or [{}])[0].get("id")
    assert wid is not None
    return int(wid)


def test_member_can_read_integration_settings_and_health(test_client: TestClient, auth_headers: dict):
    settings = test_client.get("/api/v1/integrations/settings", headers=auth_headers)
    assert settings.status_code == 200, settings.text
    assert "telegram" in settings.json()["data"]

    health = test_client.get("/api/v1/integrations/health", headers=auth_headers)
    assert health.status_code == 200, health.text
    body = health.json()["data"]
    assert "telegram_ready" in body
    assert "email_ready" in body


def test_workspace_admin_can_list_members(test_client: TestClient, auth_headers: dict):
    wid = _workspace_id(test_client, auth_headers)
    res = test_client.get(f"/api/v1/workspaces/{wid}/members", headers=auth_headers)
    assert res.status_code == 200, res.text
    members = res.json()["data"]
    assert isinstance(members, list)
    assert len(members) >= 1


def test_workspace_admin_can_patch_integration_settings(test_client: TestClient, auth_headers: dict):
    res = test_client.patch(
        "/api/v1/integrations/settings",
        headers=auth_headers,
        json={"public_base_url": "https://api.example.test"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"].get("public_base_url") == "https://api.example.test"


def test_editor_cannot_patch_integrations_or_invite(test_client: TestClient, auth_headers: dict):
    wid = _workspace_id(test_client, auth_headers)
    db = SessionLocal()
    original_role = None
    original_owner_id = None
    temp_owner_id = None
    try:
        admin = db.query(User).filter(User.user_name == "admin").first()
        ws = db.get(Workspace, wid)
        assert admin is not None and ws is not None
        member = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == admin.user_id)
            .first()
        )
        assert member is not None
        original_role = member.role
        original_owner_id = ws.owner_id

        suffix = uuid.uuid4().hex[:8]
        temp_owner = User(
            user_name=f"settings_owner_{suffix}",
            email=f"settings_owner_{suffix}@example.com",
            password="x",
            role="user",
        )
        db.add(temp_owner)
        db.flush()
        temp_owner_id = temp_owner.user_id
        ws.owner_id = temp_owner.user_id
        db.add(
            WorkspaceMember(
                workspace_id=wid,
                user_id=temp_owner.user_id,
                role="owner",
            )
        )
        member.role = "editor"
        db.commit()
    finally:
        db.close()

    patch = test_client.patch(
        "/api/v1/integrations/settings",
        headers=auth_headers,
        json={"public_base_url": "https://blocked.example.test"},
    )
    assert patch.status_code == 403

    invite = test_client.post(
        f"/api/v1/workspaces/{wid}/members",
        headers=auth_headers,
        json={"email": "blocked@example.com", "role": "viewer"},
    )
    assert invite.status_code == 403

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.user_name == "admin").first()
        ws = db.get(Workspace, wid)
        member = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == admin.user_id)
            .first()
        )
        if ws and original_owner_id is not None:
            ws.owner_id = original_owner_id
        if member and original_role:
            member.role = original_role
        if temp_owner_id:
            db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == wid,
                WorkspaceMember.user_id == temp_owner_id,
            ).delete()
            temp_user = db.get(User, temp_owner_id)
            if temp_user:
                db.delete(temp_user)
        db.commit()
    finally:
        db.close()
