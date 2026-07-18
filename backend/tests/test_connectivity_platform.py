"""Enterprise Connectivity Platform tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.connectivity.analytics import workspace_analytics
from app.connectivity.auth import validate_auth_config
from app.connectivity.mcp import negotiate_capabilities, register_mcp
from app.connectivity.policy import evaluate_connector_policy, evaluate_domain_policy
from app.connectivity.registry import connector_matrix, get_connector_meta, list_connectors
from app.connectivity.service import create_connection, get_connection, list_connections, store_credential
from app.connectivity.sync import create_sync_job
from app.connectivity.transform import normalize_record, validate_schema
from app.connectivity.plugins import get_connector_plugin, list_connector_plugins
from app.database import SessionLocal, User, init_db


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_id(db: Session) -> int:
    u = db.query(User).first()
    assert u
    return u.user_id


def test_connector_registry():
    connectors = list_connectors()
    assert len(connectors) >= 10
    assert get_connector_meta("slack")
    matrix = connector_matrix()
    assert "communication" in matrix


def test_create_connection_tenant_isolation(db: Session, user_id: int):
    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="slack", name="Team Slack")
    assert conn.id
    assert get_connection(db, conn.id, workspace_id=1)
    assert get_connection(db, conn.id, workspace_id=99999) is None


def test_store_credential(db: Session, user_id: int):
    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="github", name="GitHub Dev")
    cred = store_credential(db, connection_id=conn.id, workspace_id=1, secret_plain="ghp_test_token")
    assert cred.id


def test_auth_validation():
    ok = validate_auth_config("api_key", {"api_key": "secret"})
    assert ok["valid"]
    bad = validate_auth_config("oauth2", {})
    assert not bad["valid"]


def test_policy_engine():
    assert evaluate_connector_policy(connector_type="slack")["allowed"]
    blocked = evaluate_connector_policy(connector_type="slack", workspace_policies={"blocked_connectors": ["slack"]})
    assert not blocked["allowed"]
    assert evaluate_domain_policy("https://api.example.com")["allowed"]


def test_mcp_registration(db: Session, user_id: int):
    reg = register_mcp(db, workspace_id=1, name="Local MCP", role="server", tools=[{"name": "search"}])
    assert reg.id
    caps = negotiate_capabilities(["tools", "resources"], ["tools"])
    assert "tools" in caps["agreed"]


def test_sync_job(db: Session, user_id: int):
    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="s3", name="S3 Bucket")
    job = create_sync_job(db, connection=conn)
    assert job.status == "pending"


def test_transform():
    out = normalize_record({"a": 1, "b": 2}, {"x": "a"})
    assert out["x"] == 1
    assert validate_schema({"a": 1}, ["a"])["valid"]


def test_plugins():
    plugins = list_connector_plugins()
    assert any(p["type"] == "slack" for p in plugins)
    plugin = get_connector_plugin("slack")
    assert plugin.connector_type == "slack"


def test_connector_invoke_is_not_stubbed(db: Session, user_id: int):
    """GitHub create_issue must actually call the service and fail honestly when
    unconfigured — proving the plugin is no longer a fake-success stub."""
    import asyncio

    from app.connectivity.integration import invoke_connector_action

    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="github", name="GH Invoke")
    result = asyncio.run(
        invoke_connector_action(
            db,
            workspace_id=1,
            connection_id=conn.id,
            action="create_issue",
            params={"title": "Test", "body": "Body"},
        )
    )
    # No GitHub credentials in test workspace -> real service raises -> honest failure
    assert result["success"] is False
    assert "github" in result["message"].lower() or "not configured" in result["message"].lower()


def test_connector_unsupported_action(db: Session, user_id: int):
    import asyncio

    from app.connectivity.integration import invoke_connector_action

    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="linear", name="Linear Invoke")
    result = asyncio.run(
        invoke_connector_action(db, workspace_id=1, connection_id=conn.id, action="frobnicate")
    )
    assert result["success"] is False
    assert "unsupported" in result["message"].lower()


def test_all_cloud_connectors_registered():
    """P0: S3, Git, Dropbox, Google Drive, OneDrive, SharePoint must be real plugins."""
    from app.connectivity.plugins import get_connector_plugin

    for ctype in ("s3", "git", "dropbox", "gdrive", "onedrive", "sharepoint"):
        plugin = get_connector_plugin(ctype)
        assert plugin.connector_type in (ctype, "cloud") or plugin.__class__.__name__ != "BaseConnectorPlugin"
        # No plugin may be the removed StubCloudPlugin
        assert "stub" not in plugin.description.lower()


def test_cloud_connectors_no_creds_fail_honestly(db: Session, user_id: int):
    """Cloud connectors must return honest errors without credentials, never fake success."""
    import asyncio

    from app.connectivity.integration import invoke_connector_action

    for ctype, action in (("dropbox", "list_files"), ("gdrive", "list_files"), ("onedrive", "list_files")):
        conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type=ctype, name=f"{ctype} test")
        result = asyncio.run(
            invoke_connector_action(db, workspace_id=1, connection_id=conn.id, action=action)
        )
        assert result["success"] is False
        assert "token" in result["message"].lower() or ctype in result["message"].lower()


def test_s3_connector_reports_missing_bucket(db: Session, user_id: int):
    from app.connectivity.plugins import get_connector_plugin
    from app.connectivity.service import get_connection

    conn = create_connection(db, workspace_id=1, user_id=user_id, connector_type="s3", name="S3 test")
    plugin = get_connector_plugin("s3")
    result = plugin.test(db, get_connection(db, conn.id, workspace_id=1), secret="")
    assert result.success is False
    assert "bucket" in result.message.lower()


def test_object_storage_list_objects():
    """Local object storage now supports real listing (was missing)."""
    from app.data.storage.local import LocalObjectStorage

    storage = LocalObjectStorage()
    storage.put("ws/1/eiap_list_probe.txt", b"hello", workspace_id=None)
    listed = storage.list_objects(prefix="ws/1/", limit=50)
    assert any(o.key.endswith("eiap_list_probe.txt") for o in listed)


def test_analytics(db: Session, user_id: int):
    create_connection(db, workspace_id=1, user_id=user_id, connector_type="jira", name="Jira Cloud")
    stats = workspace_analytics(db, workspace_id=1)
    assert "connections" in stats
