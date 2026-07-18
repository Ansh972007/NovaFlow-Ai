"""Enterprise Intelligence & Autonomy Platform API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission, require_workspace_editor
from app.eiap import agent_intel, connectivity_intel, finops, governance, knowledge_intel, model_intel, workflow_intel
from app.eiap.observability import unified_health
from app.eiap.optimization import run_optimization_scan
from app.eiap.prediction import forecast
from app.eiap.recommendations import (
    get_recommendation,
    list_recommendations,
    recommendation_dict,
    set_status,
)
from app.eiap.reporting import generate_report, list_reports
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["Intelligence & Autonomy"])

_READ = require_permission(Permission.ASSISTANT_READ)


# --- Unified health & observability ---
@router.get("/eiap/health")
def api_health(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(unified_health(db, workspace_id=ctx.workspace_id))


# --- Domain intelligence ---
@router.get("/eiap/workflow")
def api_workflow(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(workflow_intel.analyze_workflows(db, workspace_id=ctx.workspace_id))


@router.get("/eiap/agents")
def api_agents(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(agent_intel.agent_scorecards(db, workspace_id=ctx.workspace_id))


@router.get("/eiap/knowledge")
def api_knowledge(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(knowledge_intel.analyze_knowledge(db, workspace_id=ctx.workspace_id))


@router.get("/eiap/connectivity")
def api_connectivity(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(connectivity_intel.analyze_connectivity(db, workspace_id=ctx.workspace_id))


# --- Model intelligence & benchmarks ---
@router.get("/eiap/models/benchmark")
def api_benchmark(days: int = Query(30, ge=1, le=180), db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(model_intel.benchmark_models(db, workspace_id=ctx.workspace_id, days=days))


@router.get("/eiap/models/recommend")
def api_model_recommend(priority: str = Query("balanced"), db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(model_intel.recommend_provider(db, workspace_id=ctx.workspace_id, priority=priority))


# --- Prediction & FinOps ---
@router.get("/eiap/predictions")
def api_predictions(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(forecast(db, workspace_id=ctx.workspace_id))


@router.get("/eiap/finops")
def api_finops(days: int = Query(30, ge=1, le=180), db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(finops.cost_analysis(db, workspace_id=ctx.workspace_id, days=days))


# --- Optimization scan (generates approval-gated recommendations) ---
@router.post("/eiap/optimize")
def api_optimize(body: dict | None = None, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    body = body or {}
    result = run_optimization_scan(
        db,
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        domains=body.get("domains"),
    )
    ctx.audit("eiap.optimize.scan", resource_type="eiap", resource_id="optimization")
    return ok(result)


# --- Recommendations (approval workflow) ---
@router.get("/eiap/recommendations")
def api_list_recommendations(
    domain: str = Query(""),
    status: str = Query(""),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    ctx=Depends(_READ),
):
    rows = list_recommendations(db, workspace_id=ctx.workspace_id, domain=domain, status=status, limit=limit)
    return ok([recommendation_dict(r) for r in rows])


@router.get("/eiap/recommendations/{rec_id}")
def api_get_recommendation(rec_id: str, db: Session = Depends(get_db), ctx=Depends(_READ)):
    rec = get_recommendation(db, rec_id, workspace_id=ctx.workspace_id)
    if not rec:
        return fail(404, "Recommendation not found")
    return ok(recommendation_dict(rec))


@router.post("/eiap/recommendations/{rec_id}/approve")
def api_approve(rec_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    rec = get_recommendation(db, rec_id, workspace_id=ctx.workspace_id)
    if not rec:
        return fail(404, "Recommendation not found")
    rec = set_status(db, rec, status="approved", reviewed_by=ctx.user.user_id)
    ctx.audit("eiap.recommendation.approve", resource_type="eiap_recommendation", resource_id=rec.id)
    return ok(recommendation_dict(rec))


@router.post("/eiap/recommendations/{rec_id}/dismiss")
def api_dismiss(rec_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    rec = get_recommendation(db, rec_id, workspace_id=ctx.workspace_id)
    if not rec:
        return fail(404, "Recommendation not found")
    rec = set_status(db, rec, status="dismissed", reviewed_by=ctx.user.user_id)
    return ok(recommendation_dict(rec))


@router.post("/eiap/recommendations/{rec_id}/applied")
def api_mark_applied(rec_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    rec = get_recommendation(db, rec_id, workspace_id=ctx.workspace_id)
    if not rec:
        return fail(404, "Recommendation not found")
    if rec.status != "approved":
        return fail(400, "Recommendation must be approved before it can be marked applied")
    rec = set_status(db, rec, status="applied", reviewed_by=ctx.user.user_id)
    ctx.audit("eiap.recommendation.applied", resource_type="eiap_recommendation", resource_id=rec.id)
    return ok(recommendation_dict(rec))


# --- Governance ---
@router.get("/eiap/governance/health")
def api_gov_health(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(governance.workspace_health_report(db, workspace_id=ctx.workspace_id))


@router.get("/eiap/governance/compliance")
def api_compliance(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(governance.compliance_report(db, workspace_id=ctx.workspace_id, days=days))


@router.get("/eiap/governance/security")
def api_security(db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(governance.security_posture(db, workspace_id=ctx.workspace_id))


# --- Reports ---
@router.post("/eiap/reports")
def api_generate_report(body: dict | None = None, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    body = body or {}
    report = generate_report(
        db,
        workspace_id=ctx.workspace_id,
        report_type=body.get("report_type") or "daily",
        organization_id=ctx.organization_id,
    )
    return ok(report)


@router.get("/eiap/reports")
def api_list_reports(report_type: str = Query(""), db: Session = Depends(get_db), ctx=Depends(_READ)):
    return ok(list_reports(db, workspace_id=ctx.workspace_id, report_type=report_type))
