"""AgentOS service — registry CRUD with tenant isolation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import SavedAgent
from app.services.agent_tools import DEFAULT_AGENT_SYSTEM, list_builtin_tools


def _safe_json(raw: str | None, default: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return default


def agent_dict(a: SavedAgent) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "desc": a.desc or "",
        "system_prompt": a.system_prompt or "",
        "tools": _safe_json(a.tools_json, []),
        "knowledge_id": a.knowledge_id,
        "status": a.status,
        "agent_type": getattr(a, "agent_type", None) or "custom",
        "lifecycle_status": getattr(a, "lifecycle_status", None) or "published",
        "version_no": getattr(a, "version_no", None) or 1,
        "capabilities": _safe_json(getattr(a, "capabilities_json", None), []),
        "policies": _safe_json(getattr(a, "policies_json", None), {}),
        "template_id": getattr(a, "template_id", None) or "",
        "metadata": _safe_json(getattr(a, "metadata_json", None), {}),
        "workspace_id": a.workspace_id,
        "owner_id": getattr(a, "owner_id", None) or a.user_id,
        "create_time": a.create_time.isoformat() if a.create_time else None,
        "update_time": a.update_time.isoformat() if a.update_time else None,
    }


def create_agent(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    name: str,
    desc: str = "",
    system_prompt: str = "",
    tools: list | None = None,
    knowledge_id: int | None = None,
    agent_type: str = "custom",
    lifecycle_status: str = "draft",
    capabilities: list | None = None,
    policies: dict | None = None,
    template_id: str = "",
    organization_id: int | None = None,
) -> SavedAgent:
    a = SavedAgent(
        id=uuid.uuid4().hex,
        name=name.strip()[:80],
        desc=(desc or "")[:500],
        system_prompt=(system_prompt or DEFAULT_AGENT_SYSTEM).strip(),
        tools_json=json.dumps((tools or ["summarize"])[:8]),
        knowledge_id=knowledge_id,
        user_id=user_id,
        workspace_id=workspace_id,
        status=1,
    )
    if hasattr(a, "agent_type"):
        a.agent_type = agent_type
    if hasattr(a, "lifecycle_status"):
        a.lifecycle_status = lifecycle_status
    if hasattr(a, "version_no"):
        a.version_no = 1
    if hasattr(a, "capabilities_json") and capabilities:
        a.capabilities_json = json.dumps(capabilities)
    if hasattr(a, "policies_json") and policies:
        a.policies_json = json.dumps(policies)
    if hasattr(a, "template_id"):
        a.template_id = template_id
    if hasattr(a, "organization_id"):
        a.organization_id = organization_id
    if hasattr(a, "owner_id"):
        a.owner_id = user_id
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def get_agent(db: Session, agent_id: str, *, workspace_id: int) -> SavedAgent | None:
    a = db.get(SavedAgent, agent_id)
    if not a or a.workspace_id != workspace_id:
        return None
    if getattr(a, "deleted_at", None):
        return None
    return a


def list_agents(
    db: Session,
    *,
    workspace_id: int,
    agent_type: str = "",
    lifecycle_status: str = "",
    limit: int = 50,
) -> list[SavedAgent]:
    q = db.query(SavedAgent).filter(SavedAgent.workspace_id == workspace_id)
    if hasattr(SavedAgent, "deleted_at"):
        q = q.filter(SavedAgent.deleted_at.is_(None))
    if agent_type and hasattr(SavedAgent, "agent_type"):
        q = q.filter(SavedAgent.agent_type == agent_type)
    if lifecycle_status and hasattr(SavedAgent, "lifecycle_status"):
        q = q.filter(SavedAgent.lifecycle_status == lifecycle_status)
    return q.order_by(SavedAgent.update_time.desc()).limit(limit).all()


def update_agent(db: Session, agent: SavedAgent, fields: dict) -> SavedAgent:
    if "name" in fields:
        agent.name = str(fields["name"]).strip()[:80]
    if "desc" in fields:
        agent.desc = str(fields.get("desc") or "").strip()[:500]
    if "system_prompt" in fields or "system" in fields:
        agent.system_prompt = str(fields.get("system_prompt") or fields.get("system") or agent.system_prompt).strip()
    if "tools" in fields:
        tools = fields.get("tools") or []
        agent.tools_json = json.dumps(tools[:8] if isinstance(tools, list) else [tools])
    if "knowledge_id" in fields:
        agent.knowledge_id = fields.get("knowledge_id")
    if "agent_type" in fields and hasattr(agent, "agent_type"):
        agent.agent_type = fields["agent_type"]
    if "capabilities" in fields and hasattr(agent, "capabilities_json"):
        agent.capabilities_json = json.dumps(fields.get("capabilities") or [])
    if "policies" in fields and hasattr(agent, "policies_json"):
        agent.policies_json = json.dumps(fields.get("policies") or {})
    agent.update_time = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


def publish_agent(db: Session, agent: SavedAgent) -> SavedAgent:
    if hasattr(agent, "lifecycle_status"):
        agent.lifecycle_status = "published"
    agent.status = 1
    if hasattr(agent, "version_no"):
        agent.version_no = (getattr(agent, "version_no", None) or 0) + 1
    agent.update_time = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


def archive_agent(db: Session, agent: SavedAgent) -> SavedAgent:
    if hasattr(agent, "lifecycle_status"):
        agent.lifecycle_status = "archived"
    agent.status = 0
    agent.update_time = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


def clone_agent(db: Session, agent: SavedAgent, *, user_id: int, name: str = "") -> SavedAgent:
    return create_agent(
        db,
        workspace_id=agent.workspace_id,
        user_id=user_id,
        name=name or f"{agent.name} (copy)",
        desc=agent.desc or "",
        system_prompt=agent.system_prompt or "",
        tools=_safe_json(agent.tools_json, []),
        knowledge_id=agent.knowledge_id,
        agent_type=getattr(agent, "agent_type", None) or "custom",
        lifecycle_status="draft",
        capabilities=_safe_json(getattr(agent, "capabilities_json", None), []),
        policies=_safe_json(getattr(agent, "policies_json", None), {}),
        template_id=getattr(agent, "template_id", None) or "",
    )


def delete_agent(db: Session, agent: SavedAgent) -> None:
    if hasattr(agent, "deleted_at"):
        agent.deleted_at = datetime.utcnow()
        if hasattr(agent, "lifecycle_status"):
            agent.lifecycle_status = "deleted"
        db.commit()
    else:
        db.delete(agent)
        db.commit()


def list_tool_catalog() -> list[dict]:
    return list_builtin_tools()
