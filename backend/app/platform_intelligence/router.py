"""Platform Intelligence API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import PlatformBudget, PlatformPolicy, get_db
from app.deps import get_workspace_ctx, require_permission
from app.platform_intelligence.admin.dashboards import (
    organization_dashboard,
    security_dashboard,
    system_dashboard,
    workspace_dashboard,
)
from app.platform_intelligence.capacity.planner import capacity_forecast
from app.platform_intelligence.events.emitter import list_events
from app.platform_intelligence.finops.ledger import (
    check_budget,
    detect_cost_anomalies,
    forecast_monthly,
    workspace_cost_summary,
)
from app.platform_intelligence.healing.detectors import detect_anomalies, recovery_recommendations
from app.platform_intelligence.observability.health import platform_health_snapshot
from app.platform_intelligence.observability.metrics import aggregate_subsystems, get_recent_metrics
from app.platform_intelligence.policy.engine import evaluate_policy, seed_default_policies
from app.platform_intelligence.tracing.context import get_trace_id
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["Platform Intelligence"])


@router.get("/platform/intelligence/health")
def pi_health():
    return ok(platform_health_snapshot())


@router.get("/platform/intelligence/trace")
def current_trace(ctx=Depends(get_workspace_ctx)):
    return ok({"trace_id": get_trace_id(), "workspace_id": ctx.workspace_id})


@router.get("/platform/intelligence/metrics")
def pi_metrics(
    subsystem: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    return ok({"metrics": get_recent_metrics(subsystem=subsystem, limit=limit), "aggregate": aggregate_subsystems()})


@router.get("/platform/intelligence/dashboard/system")
def dashboard_system(ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(system_dashboard())


@router.get("/platform/intelligence/dashboard/workspace")
def dashboard_workspace(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(workspace_dashboard(db, ctx.workspace_id))


@router.get("/platform/intelligence/dashboard/organization")
def dashboard_organization(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    if not ctx.organization_id:
        return fail(400, "Organization context required")
    return ok(organization_dashboard(db, ctx.organization_id))


@router.get("/platform/intelligence/dashboard/security")
def dashboard_security(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(security_dashboard(db, ctx.workspace_id))


@router.get("/platform/intelligence/dashboard/billing")
def dashboard_billing(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(
        {
            "cost": workspace_cost_summary(db, ctx.workspace_id),
            "budget": check_budget(db, ctx.workspace_id),
            "forecast": forecast_monthly(db, ctx.workspace_id),
            "anomalies": detect_cost_anomalies(db, ctx.workspace_id),
        }
    )


@router.get("/platform/intelligence/dashboard/incidents")
def dashboard_incidents(ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok({"anomalies": detect_anomalies(), "recovery": recovery_recommendations()})


@router.get("/platform/intelligence/events")
def pi_events(
    event_type: str | None = Query(None),
    trace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ANALYTICS_READ)),
):
    return ok(list_events(db, workspace_id=ctx.workspace_id, event_type=event_type, trace_id=trace_id, limit=limit))


@router.get("/platform/intelligence/capacity")
def pi_capacity(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(capacity_forecast(db, ctx.workspace_id))


@router.get("/platform/intelligence/policies")
def list_policies(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    from app.database import PlatformPolicy

    rows = (
        db.query(PlatformPolicy)
        .filter(
            (PlatformPolicy.workspace_id == ctx.workspace_id) | (PlatformPolicy.workspace_id.is_(None))
        )
        .all()
    )
    return ok(
        [
            {
                "id": r.id,
                "policy_type": r.policy_type,
                "scope": r.scope,
                "rule_key": r.rule_key,
                "rule_value": r.rule_value,
                "severity": r.severity,
                "enabled": bool(r.enabled),
            }
            for r in rows
        ]
    )


@router.post("/platform/intelligence/policies/seed")
def seed_policies(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.WORKSPACE_WRITE))):
    count = seed_default_policies(db, ctx.workspace_id)
    ctx.audit("platform.policy.seed", detail={"count": count})
    return ok({"seeded": count})


@router.post("/platform/intelligence/policies/evaluate")
def evaluate_policies(body: dict, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    decision = evaluate_policy(
        db,
        body.get("policy_type") or "*",
        body.get("context") or {},
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
    )
    return ok({"allowed": decision.allowed, "reason": decision.reason, "matched_rules": decision.matched_rules})


@router.get("/platform/intelligence/budget")
def get_budget(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ANALYTICS_READ))):
    return ok(check_budget(db, ctx.workspace_id))


@router.put("/platform/intelligence/budget")
def set_budget(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.WORKSPACE_WRITE))):
    limit = float(body.get("monthly_limit_usd") or 0)
    row = (
        db.query(PlatformBudget)
        .filter(PlatformBudget.workspace_id == ctx.workspace_id)
        .first()
    )
    if not row:
        row = PlatformBudget(workspace_id=ctx.workspace_id, organization_id=ctx.organization_id)
        db.add(row)
    row.monthly_limit_usd = limit
    row.enabled = 1 if limit > 0 else 0
    db.commit()
    ctx.audit("platform.budget.update", detail={"monthly_limit_usd": limit})
    return ok({"monthly_limit_usd": limit, "enabled": bool(row.enabled)})
