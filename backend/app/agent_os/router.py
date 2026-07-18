"""Enterprise Agent OS API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agent_os.analytics import failure_analysis, workspace_agent_analytics
from app.agent_os.export import export_agent, import_agent_config
from app.agent_os.hitl import request_approval, submit_feedback
from app.agent_os.integration import execute_agent
from app.agent_os.planning import create_plan_session, plan_dict, replan
from app.agent_os.registry import get_template, list_agent_types, list_templates
from app.agent_os.service import (
    agent_dict,
    archive_agent,
    clone_agent,
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    list_tool_catalog,
    publish_agent,
    update_agent,
)
from app.agent_os.supervisor import supervise_plan
from app.agent_os.tasks import cancel_run, get_run, pause_run, resume_run, run_dict
from app.agent_os.verification import report_dict
from app.database import AgentPlanSession, AgentVerificationReport, get_db
from app.deps import get_workspace_ctx, require_permission, require_workspace_editor
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["Agent OS"])


@router.get("/agent-os/types")
def api_agent_types(ctx=Depends(get_workspace_ctx)):
    return ok(list_agent_types())


@router.get("/agent-os/templates")
def api_templates(ctx=Depends(get_workspace_ctx)):
    return ok(list_templates())


@router.get("/agent-os/templates/{template_id}")
def api_get_template(template_id: str, ctx=Depends(get_workspace_ctx)):
    tpl = get_template(template_id)
    if not tpl:
        return fail(404, "Template not found")
    return ok(tpl)


@router.get("/agent-os/tools")
def api_tools(ctx=Depends(get_workspace_ctx)):
    return ok(list_tool_catalog())


@router.post("/agent-os/agents")
def api_create_agent(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "name required")
    a = create_agent(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        organization_id=ctx.organization_id,
        name=name,
        desc=body.get("desc") or "",
        system_prompt=body.get("system_prompt") or body.get("system") or "",
        tools=body.get("tools"),
        knowledge_id=body.get("knowledge_id"),
        agent_type=body.get("agent_type") or "custom",
        lifecycle_status=body.get("lifecycle_status") or "draft",
        capabilities=body.get("capabilities"),
        policies=body.get("policies"),
        template_id=body.get("template_id") or "",
    )
    ctx.audit("agent_os.create", resource_type="agent", resource_id=a.id)
    return ok(agent_dict(a))


@router.get("/agent-os/agents")
def api_list_agents(
    agent_type: str = Query(""),
    lifecycle_status: str = Query(""),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.AGENT_READ)),
):
    rows = list_agents(db, workspace_id=ctx.workspace_id, agent_type=agent_type, lifecycle_status=lifecycle_status)
    return ok([agent_dict(r) for r in rows])


@router.get("/agent-os/agents/{agent_id}")
def api_get_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    return ok(agent_dict(a))


@router.put("/agent-os/agents/{agent_id}")
def api_update_agent(agent_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    a = update_agent(db, a, body)
    return ok(agent_dict(a))


@router.delete("/agent-os/agents/{agent_id}")
def api_delete_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    delete_agent(db, a)
    return ok({"deleted": agent_id})


@router.post("/agent-os/agents/{agent_id}/publish")
def api_publish_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    a = publish_agent(db, a)
    ctx.audit("agent_os.publish", resource_type="agent", resource_id=a.id)
    return ok(agent_dict(a))


@router.post("/agent-os/agents/{agent_id}/archive")
def api_archive_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    a = archive_agent(db, a)
    return ok(agent_dict(a))


@router.post("/agent-os/agents/{agent_id}/clone")
def api_clone_agent(agent_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    clone = clone_agent(db, a, user_id=ctx.user.user_id, name=body.get("name") or "")
    return ok(agent_dict(clone))


@router.get("/agent-os/agents/{agent_id}/export")
def api_export_agent(agent_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    a = get_agent(db, agent_id, workspace_id=ctx.workspace_id)
    if not a:
        return fail(404, "Agent not found")
    return ok(export_agent(a))


@router.post("/agent-os/agents/import")
def api_import_agent(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    cfg = import_agent_config(body)
    a = create_agent(db, workspace_id=ctx.workspace_id, user_id=ctx.user.user_id, **cfg)
    return ok(agent_dict(a))


@router.post("/agent-os/execute")
async def api_execute(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
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
            system=body.get("system") or "",
            knowledge_id=body.get("knowledge_id"),
            conversation_id=body.get("conversation_id"),
            mode=body.get("mode") or "single",
            roles=body.get("roles"),
            agent_type=body.get("agent_type") or "custom",
            verify=body.get("verify", True),
        )
        return ok(result)
    except Exception as exc:
        return fail(400, str(exc))


@router.get("/agent-os/runs/{run_id}")
def api_get_run(run_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    run = get_run(db, run_id, workspace_id=ctx.workspace_id)
    if not run:
        return fail(404, "Run not found")
    return ok(run_dict(run))


@router.post("/agent-os/runs/{run_id}/pause")
def api_pause_run(run_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    run = get_run(db, run_id, workspace_id=ctx.workspace_id)
    if not run:
        return fail(404, "Run not found")
    from app.agent_os.tasks import pause_run

    cp = pause_run(db, run, state=body.get("state"), step_no=int(body.get("step_no") or 0))
    return ok({"run_id": run_id, "checkpoint_id": cp.id, "status": run.status})


@router.post("/agent-os/runs/{run_id}/resume")
def api_resume_run(run_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    run = get_run(db, run_id, workspace_id=ctx.workspace_id)
    if not run:
        return fail(404, "Run not found")
    try:
        run = resume_run(db, run)
    except ValueError as exc:
        return fail(400, str(exc))
    return ok(run_dict(run))


@router.post("/agent-os/runs/{run_id}/cancel")
def api_cancel_run(run_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    run = get_run(db, run_id, workspace_id=ctx.workspace_id)
    if not run:
        return fail(404, "Run not found")
    run = cancel_run(db, run)
    return ok(run_dict(run))


@router.post("/agent-os/runs/{run_id}/approve")
def api_approve_run(run_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    run = get_run(db, run_id, workspace_id=ctx.workspace_id)
    if not run:
        return fail(404, "Run not found")
    if body.get("request"):
        hitl = request_approval(db, run, reason=body.get("reason") or "Approval required")
        return ok(hitl)
    hitl = submit_feedback(db, run, approved=bool(body.get("approved", True)), feedback=body.get("feedback") or "")
    return ok(hitl)


@router.post("/agent-os/plan")
def api_plan(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    goal = (body.get("goal") or body.get("input") or "").strip()
    if not goal:
        return fail(400, "goal required")
    session = create_plan_session(db, workspace_id=ctx.workspace_id, goal=goal, run_id=body.get("run_id"))
    return ok(plan_dict(session))


@router.post("/agent-os/plan/{plan_id}/replan")
def api_replan(plan_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    session = db.get(AgentPlanSession, plan_id)
    if not session or session.workspace_id != ctx.workspace_id:
        return fail(404, "Plan not found")
    plan = replan(db, session, new_goal=body.get("goal") or "")
    return ok({"plan_id": plan_id, "plan": plan})


@router.post("/agent-os/supervisor/plan")
def api_supervisor_plan(body: dict, ctx=Depends(require_permission(Permission.AGENT_READ))):
    goal = (body.get("goal") or body.get("input") or "").strip()
    if not goal:
        return fail(400, "goal required")
    return ok(supervise_plan(goal, agent_type=body.get("agent_type") or "supervisor"))


@router.get("/agent-os/runs/{run_id}/verification")
def api_verification(run_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    rec = (
        db.query(AgentVerificationReport)
        .filter(AgentVerificationReport.run_id == run_id, AgentVerificationReport.workspace_id == ctx.workspace_id)
        .order_by(AgentVerificationReport.create_time.desc())
        .first()
    )
    if not rec:
        return fail(404, "Verification report not found")
    return ok(report_dict(rec))


@router.get("/agent-os/analytics")
def api_analytics(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    return ok(workspace_agent_analytics(db, workspace_id=ctx.workspace_id))


@router.get("/agent-os/analytics/failures")
def api_failures(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.AGENT_READ))):
    return ok(failure_analysis(db, workspace_id=ctx.workspace_id))


@router.get("/agent-os/plugins")
def api_plugins(ctx=Depends(get_workspace_ctx)):
    from app.agent_os.plugins import list_plugins

    return ok(list_plugins())
