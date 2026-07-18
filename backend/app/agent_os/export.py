"""AgentOS export/import."""

from __future__ import annotations

import json
from typing import Any

from app.database import SavedAgent
from app.agent_os.service import agent_dict


def export_agent(agent: SavedAgent) -> dict[str, Any]:
    data = agent_dict(agent)
    return {"format": "json", "agent": data}


def import_agent_config(data: dict) -> dict[str, Any]:
    agent_data = data.get("agent") or data
    return {
        "name": agent_data.get("name") or "Imported Agent",
        "desc": agent_data.get("desc") or "",
        "system_prompt": agent_data.get("system_prompt") or "",
        "tools": agent_data.get("tools") or ["summarize"],
        "knowledge_id": agent_data.get("knowledge_id"),
        "agent_type": agent_data.get("agent_type") or "custom",
        "capabilities": agent_data.get("capabilities") or [],
        "policies": agent_data.get("policies") or {},
    }
