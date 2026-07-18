"""Workflow Intelligence API — additive endpoints, existing APIs unchanged."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowRun, WorkflowTestCase, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.runtime.context import runtime_from_platform
from app.schemas import fail, ok
from app.workflow_intelligence.copilot import (
    copilot_explain,
    copilot_fix,
    copilot_generate_tests,
    copilot_suggest,
)
from app.workflow_intelligence.debugger import build_debug_session, replay_steps
from app.workflow_intelligence.graph.parser import parse_graph
from app.workflow_intelligence.graph.validator import validate_graph
from app.workflow_intelligence.observability import analyze_run, workspace_run_stats
from app.workflow_intelligence.optimizer import optimize_graph
from app.workflow_intelligence.planner import plan_workflow_from_text
from app.workflow_intelligence.publish_gate import check_publish_ready
from app.workflow_intelligence.security import validate_workflow_security
from app.workflow_intelligence.testing.runner import run_saved_tests, run_test_case

router = APIRouter(tags=["Workflow Intelligence"])


@router.post("/workflow/intelligence/validate")
def validate_workflow(body: dict, ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, body.get("workflow_id") or body.get("id"))
    graph_raw = body.get("graph") or (w.graph_json if w else None)
    if not graph_raw:
        return fail(400, "workflow_id or graph required")
    graph = parse_graph(graph_raw)
    report = validate_graph(graph, workspace_id=ctx.workspace_id)
    security = validate_workflow_security(graph)
    return ok({"validation": report.to_dict(), "security": security.to_dict()})


@router.post("/workflow/intelligence/publish-check")
def publish_check(body: dict, ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, body.get("workflow_id") or body.get("id"))
    if not w:
        return fail(404, "Workflow not found")
    graph = parse_graph(w.graph_json)
    return ok(check_publish_ready(graph))


@router.post("/workflow/intelligence/plan")
async def plan_workflow(body: dict, ctx=Depends(require_workspace_editor)):
    description = (body.get("description") or body.get("prompt") or "").strip()
    if not description:
        return fail(400, "description required")
    rt = runtime_from_platform(ctx)
    plan = await plan_workflow_from_text(rt, description)
    ctx.audit("workflow.intelligence.plan", detail={"summary": plan.summary[:120]})
    return ok(plan.to_dict())


@router.post("/workflow/intelligence/optimize")
def optimize_workflow(body: dict, ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, body.get("workflow_id") or body.get("id"))
    graph_raw = body.get("graph") or (w.graph_json if w else None)
    if not graph_raw:
        return fail(400, "workflow_id or graph required")
    report = optimize_graph(parse_graph(graph_raw))
    return ok(report.to_dict())


@router.get("/workflow/intelligence/runs/{run_id}/debug")
def debug_run(run_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    run = ctx.fetch(WorkflowRun, run_id)
    if not run:
        return fail(404, "Run not found")
    wf = ctx.fetch(Workflow, run.workflow_id)
    graph = json.loads(wf.graph_json or "{}") if wf else {}
    session = build_debug_session(db, run, graph)
    metrics = analyze_run(run)
    return ok({**session.to_dict(), "metrics": metrics.to_dict()})


@router.get("/workflow/intelligence/runs/{run_id}/replay")
def replay_run(run_id: int, ctx=Depends(get_workspace_ctx)):
    run = ctx.fetch(WorkflowRun, run_id)
    if not run:
        return fail(404, "Run not found")
    try:
        steps = json.loads(run.steps_json or "[]")
    except json.JSONDecodeError:
        steps = []
    return ok({"steps": replay_steps(steps), "input": run.input_text, "output": run.output_text})


@router.get("/workflow/intelligence/observability")
def workflow_observability(
    limit: int = Query(100, ge=1, le=500),
    ctx=Depends(get_workspace_ctx),
):
    return ok(workspace_run_stats(ctx.db, ctx.workspace_id, limit=limit))


@router.post("/workflow/intelligence/copilot/explain")
async def copilot_explain_api(body: dict, ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, body.get("workflow_id"))
    graph = body.get("graph") or (w.graph_json if w else None)
    if not graph:
        return fail(400, "workflow_id or graph required")
    text = await copilot_explain(runtime_from_platform(ctx), graph)
    return ok({"explanation": text})


@router.post("/workflow/intelligence/copilot/fix")
async def copilot_fix_api(body: dict, ctx=Depends(require_workspace_editor)):
    w = ctx.fetch(Workflow, body.get("workflow_id"))
    graph = body.get("graph") or (w.graph_json if w else None)
    issue = (body.get("issue") or "").strip() or "Fix validation errors"
    if not graph:
        return fail(400, "workflow_id or graph required")
    result = await copilot_fix(runtime_from_platform(ctx), graph, issue)
    return ok(result)


@router.post("/workflow/intelligence/copilot/suggest")
async def copilot_suggest_api(body: dict, ctx=Depends(get_workspace_ctx)):
    w = ctx.fetch(Workflow, body.get("workflow_id"))
    graph = body.get("graph") or (w.graph_json if w else None)
    if not graph:
        return fail(400, "workflow_id or graph required")
    result = await copilot_suggest(runtime_from_platform(ctx), graph)
    return ok(result)


@router.post("/workflow/intelligence/copilot/tests")
async def copilot_tests_api(body: dict, ctx=Depends(require_workspace_editor)):
    w = ctx.fetch(Workflow, body.get("workflow_id"))
    graph = body.get("graph") or (w.graph_json if w else None)
    if not graph:
        return fail(400, "workflow_id or graph required")
    tests = await copilot_generate_tests(runtime_from_platform(ctx), graph)
    return ok({"tests": tests})


@router.post("/workflow/intelligence/tests")
def create_test_case(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    wf_id = body.get("workflow_id")
    w = ctx.fetch(Workflow, wf_id)
    if not w:
        return fail(404, "Workflow not found")
    row = WorkflowTestCase(
        workflow_id=wf_id,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        name=(body.get("name") or "Test")[:120],
        input_text=(body.get("input_text") or body.get("input") or "")[:4000],
        expected_contains=(body.get("expected_contains") or "")[:2000],
        mock_mode=1 if body.get("mock_mode") else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ctx.audit("workflow.test.create", resource_type="workflow", resource_id=wf_id)
    return ok({"id": row.id, "name": row.name})


@router.get("/workflow/intelligence/tests")
def list_test_cases(workflow_id: str = Query(...), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(WorkflowTestCase)
        .filter(WorkflowTestCase.workflow_id == workflow_id, WorkflowTestCase.deleted_at.is_(None))
        .order_by(WorkflowTestCase.create_time.desc())
        .all()
    )
    return ok(
        [
            {
                "id": r.id,
                "name": r.name,
                "input_text": r.input_text,
                "expected_contains": r.expected_contains,
                "mock_mode": bool(r.mock_mode),
            }
            for r in rows
        ]
    )


@router.post("/workflow/intelligence/tests/run")
async def run_tests(body: dict, ctx=Depends(require_workspace_editor)):
    wf_id = body.get("workflow_id")
    if not wf_id:
        return fail(400, "workflow_id required")
    results = await run_saved_tests(
        ctx.db, wf_id, user_id=ctx.user.user_id, workspace_id=ctx.workspace_id
    )
    passed = sum(1 for r in results if r.passed)
    ctx.audit("workflow.test.run", detail={"passed": passed, "total": len(results)}, resource_id=wf_id)
    return ok({"results": [r.to_dict() for r in results], "passed": passed, "total": len(results)})


@router.post("/workflow/intelligence/tests/run-one")
async def run_one_test(body: dict, ctx=Depends(require_workspace_editor)):
    w = ctx.fetch(Workflow, body.get("workflow_id"))
    if not w:
        return fail(404, "Workflow not found")
    result = await run_test_case(
        ctx.db,
        w,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        input_text=(body.get("input_text") or body.get("input") or "").strip(),
        expected_contains=(body.get("expected_contains") or "").strip(),
        mock_mode=bool(body.get("mock_mode")),
    )
    return ok(result.to_dict())
