import json
from sqlalchemy.orm import Session
from app.database import SavedAgent

def provision_agent_topology(db: Session, workspace_id: int, name: str, agent_type: str, tools: list[str]) -> SavedAgent:
    """Configures agent topologies (e.g. multi-agent supervisor or validation agent) autonomously."""
    agent = SavedAgent(
        workspace_id=workspace_id,
        name=name,
        tools_json=json.dumps(tools),
        system_prompt=f"You are an enterprise {name} executing under strict policies.",
        agent_type=agent_type,
        lifecycle_status="active",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
