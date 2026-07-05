from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.agent_tools import list_builtin_tools, run_agent

router = APIRouter(tags=["Agents"])


@router.get("/agents/tools")
def get_tools():
    return ok(list_builtin_tools())


@router.post("/agents/run")
async def run_agent_api(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    user_input = (body.get("input") or body.get("message") or "").strip()
    if not user_input:
        return fail(400, "input required")
    tools = body.get("tools") or ["summarize"]
    try:
        output = await run_agent(
            db,
            user_input,
            tools if isinstance(tools, list) else [tools],
            knowledge_id=body.get("knowledge_id"),
            workspace_id=ctx.workspace_id,
            system=(body.get("system") or "You are a helpful NovaFlow agent."),
        )
        return ok({"output": output, "tools": tools})
    except Exception as exc:
        return fail(400, str(exc))
