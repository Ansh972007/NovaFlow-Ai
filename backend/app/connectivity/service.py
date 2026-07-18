"""ECP service — connection CRUD with tenant isolation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.registry import get_connector_meta
from app.database import ConnectorConnection, ConnectorCredential


def _safe_json(raw: str | None, default: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return default


def connection_dict(conn: ConnectorConnection) -> dict[str, Any]:
    meta = get_connector_meta(conn.connector_type) or {}
    return {
        "id": conn.id,
        "name": conn.name,
        "connector_type": conn.connector_type,
        "category": meta.get("category"),
        "auth_type": conn.auth_type,
        "status": conn.status,
        "lifecycle_status": conn.lifecycle_status,
        "capabilities": _safe_json(conn.capabilities_json, meta.get("capabilities") or []),
        "config": _safe_json(conn.config_json, {}),
        "health_status": conn.health_status,
        "last_health_at": conn.last_health_at.isoformat() if conn.last_health_at else None,
        "version_no": conn.version_no,
        "workspace_id": conn.workspace_id,
        "organization_id": conn.organization_id,
        "create_time": conn.create_time.isoformat() if conn.create_time else None,
    }


def create_connection(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    connector_type: str,
    name: str,
    auth_type: str = "api_key",
    config: dict | None = None,
    organization_id: int | None = None,
    lifecycle_status: str = "published",
) -> ConnectorConnection:
    meta = get_connector_meta(connector_type)
    if not meta:
        raise ValueError(f"Unknown connector type: {connector_type}")
    conn = ConnectorConnection(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=connector_type,
        name=name.strip()[:120],
        auth_type=auth_type,
        lifecycle_status=lifecycle_status,
        capabilities_json=json.dumps(meta.get("capabilities") or []),
        config_json=json.dumps(config or {}),
        created_by=user_id,
        health_status="unknown",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def get_connection(db: Session, connection_id: str, *, workspace_id: int) -> ConnectorConnection | None:
    conn = db.get(ConnectorConnection, connection_id)
    if not conn or conn.workspace_id != workspace_id:
        return None
    if conn.status == "deleted":
        return None
    return conn


def list_connections(
    db: Session,
    *,
    workspace_id: int,
    connector_type: str = "",
    limit: int = 50,
) -> list[ConnectorConnection]:
    q = db.query(ConnectorConnection).filter(
        ConnectorConnection.workspace_id == workspace_id,
        ConnectorConnection.status != "deleted",
    )
    if connector_type:
        q = q.filter(ConnectorConnection.connector_type == connector_type)
    return q.order_by(ConnectorConnection.update_time.desc()).limit(limit).all()


def update_connection(db: Session, conn: ConnectorConnection, fields: dict) -> ConnectorConnection:
    if "name" in fields:
        conn.name = str(fields["name"]).strip()[:120]
    if "config" in fields:
        conn.config_json = json.dumps(fields.get("config") or {})
    if "auth_type" in fields:
        conn.auth_type = fields["auth_type"]
    if "status" in fields:
        conn.status = fields["status"]
    conn.version_no = (conn.version_no or 1) + 1
    conn.update_time = datetime.utcnow()
    db.commit()
    db.refresh(conn)
    return conn


def delete_connection(db: Session, conn: ConnectorConnection) -> None:
    conn.status = "deleted"
    conn.lifecycle_status = "archived"
    conn.update_time = datetime.utcnow()
    db.commit()


def store_credential(
    db: Session,
    *,
    connection_id: str,
    workspace_id: int,
    secret_plain: str,
    credential_type: str = "secret",
) -> ConnectorCredential:
    from app.connectivity.secrets import encrypt_credential

    cred = ConnectorCredential(
        id=uuid.uuid4().hex,
        connection_id=connection_id,
        workspace_id=workspace_id,
        credential_type=credential_type,
        secret_enc=encrypt_credential(secret_plain),
        version_no=1,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def get_latest_credential(db: Session, connection_id: str, *, workspace_id: int) -> ConnectorCredential | None:
    return (
        db.query(ConnectorCredential)
        .filter(ConnectorCredential.connection_id == connection_id, ConnectorCredential.workspace_id == workspace_id)
        .order_by(ConnectorCredential.version_no.desc())
        .first()
    )
