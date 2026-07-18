from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SavedAgent, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.agent_tools import DEFAULT_AGENT_SYSTEM, list_builtin_tools
import json
import uuid

router = APIRouter(tags=["Agents"])


def agent_dict(a: SavedAgent) -> dict:
    try:
        tools = json.loads(a.tools_json or "[]")
    except json.JSONDecodeError:
        tools = []
    return {
        "id": a.id,
        "name": a.name,
        "desc": a.desc or "",
        "system_prompt": a.system_prompt or "",
        "tools": tools if isinstance(tools, list) else [],
        "knowledge_id": a.knowledge_id,
        "status": a.status,
        "create_time": a.create_time.isoformat() if a.create_time else None,
        "update_time": a.update_time.isoformat() if a.update_time else None,
    }


@router.get("/agents/tools")
def get_tools():
    return ok(list_builtin_tools())


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(SavedAgent)
        
        .order_by(SavedAgent.update_time.desc())
        .all()
    )
    return ok([agent_dict(r) for r in rows])


@router.post("/agents")
def create_agent(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "name required")
    tools = body.get("tools") or ["summarize"]
    if not isinstance(tools, list):
        tools = [tools]
    a = SavedAgent(
        id=uuid.uuid4().hex,
        name=name[:80],
        desc=(body.get("desc") or "").strip()[:500],
        system_prompt=(body.get("system_prompt") or body.get("system") or DEFAULT_AGENT_SYSTEM).strip(),
        tools_json=json.dumps(tools[:5]),
        knowledge_id=body.get("knowledge_id"),
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        status=1 if body.get("status", 1) else 0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return ok(agent_dict(a))


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = ctx.fetch(SavedAgent, agent_id)
    if not a:
        return fail(404, "Agent not found")
    if "name" in body:
        a.name = str(body.get("name") or a.name).strip()[:80]
    if "desc" in body:
        a.desc = str(body.get("desc") or "").strip()[:500]
    if "system_prompt" in body or "system" in body:
        a.system_prompt = str(body.get("system_prompt") or body.get("system") or a.system_prompt).strip()
    if "tools" in body:
        tools = body.get("tools") or []
        if not isinstance(tools, list):
            tools = [tools]
        a.tools_json = json.dumps(tools[:5])
    if "knowledge_id" in body:
        a.knowledge_id = body.get("knowledge_id")
    if "status" in body:
        a.status = 1 if body["status"] else 0
    a.update_time = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return ok(agent_dict(a))


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = ctx.fetch(SavedAgent, agent_id)
    if not a:
        return fail(404, "Agent not found")
    db.delete(a)
    db.commit()
    return ok({"deleted": agent_id})


@router.post("/agents/run")
async def run_agent_api(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    from app.agent_os.integration import execute_agent

    user_input = (body.get("input") or body.get("message") or "").strip()
    if not user_input:
        return fail(400, "input required")

    try:
        result = await execute_agent(
            db,
            ctx,
            user_input=user_input,
            agent_id=(body.get("agent_id") or "").strip(),
            tools=body.get("tools"),
            system=body.get("system") or DEFAULT_AGENT_SYSTEM,
            knowledge_id=body.get("knowledge_id"),
            conversation_id=body.get("conversation_id"),
            mode=body.get("mode") or "single",
            roles=body.get("roles"),
            agent_type=body.get("agent_type") or "custom",
        )
        return ok(
            {
                "output": result.get("output"),
                "tool_results": result.get("tool_results"),
                "tools": body.get("tools"),
                "selected_tools": result.get("selected_tools"),
                "metrics": result.get("metrics"),
                "conversation_id": result.get("conversation_id"),
                "run_id": result.get("run_id"),
                "confidence": result.get("confidence"),
                "verification": result.get("verification"),
            }
        )
    except Exception as exc:
        return fail(400, str(exc))
