"""ECP Model Context Protocol support."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.database import MCPRegistration


def register_mcp(
    db: Session,
    *,
    workspace_id: int,
    name: str,
    role: str = "client",
    transport: str = "stdio",
    endpoint: str = "",
    capabilities: list | None = None,
    tools: list | None = None,
    auth_type: str = "none",
    config: dict | None = None,
    organization_id: int | None = None,
    version: str = "1.0",
) -> MCPRegistration:
    reg = MCPRegistration(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name=name.strip()[:120],
        role=role,
        transport=transport,
        endpoint=endpoint[:500],
        capabilities_json=json.dumps(capabilities or []),
        tools_json=json.dumps(tools or []),
        auth_type=auth_type,
        version=version,
        config_json=json.dumps(config or {}),
        status="active",
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


def discover_tools(reg: MCPRegistration) -> list[dict[str, Any]]:
    tools = json.loads(reg.tools_json or "[]")
    if tools:
        return tools
    return [{"name": "ping", "description": "MCP health check"}]


def negotiate_capabilities(client_caps: list[str], server_caps: list[str]) -> dict[str, Any]:
    agreed = [c for c in client_caps if c in server_caps]
    return {
        "client": client_caps,
        "server": server_caps,
        "agreed": agreed,
        "version": "1.0",
    }


def mcp_dict(reg: MCPRegistration) -> dict[str, Any]:
    return {
        "id": reg.id,
        "name": reg.name,
        "role": reg.role,
        "transport": reg.transport,
        "endpoint": reg.endpoint,
        "capabilities": json.loads(reg.capabilities_json or "[]"),
        "tools": json.loads(reg.tools_json or "[]"),
        "auth_type": reg.auth_type,
        "version": reg.version,
        "status": reg.status,
        "workspace_id": reg.workspace_id,
    }


def list_mcp_registrations(db: Session, *, workspace_id: int, role: str = "") -> list[MCPRegistration]:
    q = db.query(MCPRegistration).filter(MCPRegistration.workspace_id == workspace_id, MCPRegistration.status == "active")
    if role:
        q = q.filter(MCPRegistration.role == role)
    return q.order_by(MCPRegistration.update_time.desc()).all()
