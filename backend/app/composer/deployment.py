import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.composer.agent_composer import provision_agent_topology
from app.composer.workflow_composer import assemble_executable_workflow
from app.database import ProjectGraph, SolutionGraph, User, Workflow

def deploy_solution_graph(
    db: Session,
    workspace_id: int,
    solution_id: str,
    *,
    user_id: int | None = None,
    knowledge_id: int | None = None,
) -> dict:
    """Deploy solution and create concrete runtime artifacts."""
    solution = db.query(SolutionGraph).filter(SolutionGraph.id == solution_id).first()
    if not solution:
        raise ValueError("Solution graph not found.")
    project = db.query(ProjectGraph).filter(ProjectGraph.id == solution.project_id).first()
    if not project or int(project.workspace_id or 0) != int(workspace_id):
        raise ValueError("Project not found for workspace.")

    payload = json.loads(solution.graph_payload or "{}")
    nodes = payload.get("nodes") or {}
    node_values = list(nodes.values()) if isinstance(nodes, dict) else (nodes or [])

    # 1) Build workflow artifact
    actor_id = user_id
    if not actor_id:
        actor = db.query(User).order_by(User.user_id.asc()).first()
        actor_id = actor.user_id if actor else 1
    workflow = assemble_executable_workflow(
        db,
        workspace_id=workspace_id,
        user_id=actor_id,
        solution_id=solution.id,
        knowledge_id=knowledge_id,
    )
    if isinstance(workflow, Workflow):
        workflow.status = 1
        db.commit()
        db.refresh(workflow)

    # 2) Build agent artifact when graph implies agentic orchestration
    wants_agent = any(
        str((n or {}).get("type", "")).lower() in {"agent", "capability"}
        for n in node_values
    )
    agent = None
    if wants_agent:
        tools = ["summarize", "kb_search"]
        if any("telegram" in str((n or {}).get("id", "")).lower() for n in node_values):
            tools.append("telegram_send")
        agent = provision_agent_topology(
            db,
            workspace_id=workspace_id,
            name=f"AIOS Agent {solution.id[:8]}",
            agent_type="supervisor",
            tools=list(dict.fromkeys(tools)),
            user_id=actor_id,
        )

    # 3) Mark statuses and return links for UI
    solution.status = "deployed"
    project.status = "deployed"
    db.commit()
    docs_link = f"/api/v1/aios/project/{project.id}/docs"
    return {
        "project_id": project.id,
        "solution_id": solution_id,
        "status": "deployed",
        "workflow_id": workflow.id if workflow else None,
        "agent_id": agent.id if agent else None,
        "links": {
            "workflow": f"/workflows/{workflow.id}" if workflow else "",
            "agent": f"/agents/{agent.id}" if agent else "",
            "docs": docs_link,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
