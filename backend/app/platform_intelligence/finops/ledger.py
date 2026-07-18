"""FinOps — cost tracking, budgets, forecasts, anomalies."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.receipt import estimate_cost_usd


def record_cost(
    db: Session,
    *,
    workspace_id: int,
    organization_id: int | None,
    cost_type: str,
    amount_usd: float,
    trace_id: str = "",
    model: str = "",
    resource_type: str = "",
    resource_id: str = "",
    meta: dict | None = None,
) -> None:
    from app.database import CostLedger

    row = CostLedger(
        workspace_id=workspace_id,
        organization_id=organization_id,
        cost_type=cost_type,
        amount_usd=round(amount_usd, 6),
        trace_id=trace_id,
        model=model or "",
        resource_type=resource_type,
        resource_id=str(resource_id or ""),
        meta_json=json.dumps(meta or {}),
    )
    db.add(row)
    db.commit()


def workspace_cost_summary(db: Session, workspace_id: int, *, days: int = 30) -> dict[str, Any]:
    from app.database import CostLedger

    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(CostLedger.cost_type, func.sum(CostLedger.amount_usd))
        .filter(CostLedger.workspace_id == workspace_id, CostLedger.create_time >= since)
        .group_by(CostLedger.cost_type)
        .all()
    )
    by_type = {str(t): round(float(a or 0), 6) for t, a in rows}
    total = round(sum(by_type.values()), 6)
    return {"workspace_id": workspace_id, "days": days, "total_usd": total, "by_type": by_type}


def check_budget(db: Session, workspace_id: int) -> dict[str, Any]:
    from app.database import PlatformBudget
    from app.platform_intelligence.policy.engine import evaluate_policy

    budget = (
        db.query(PlatformBudget)
        .filter(PlatformBudget.workspace_id == workspace_id, PlatformBudget.enabled == 1)
        .order_by(PlatformBudget.create_time.desc())
        .first()
    )
    summary = workspace_cost_summary(db, workspace_id, days=30)
    current = summary["total_usd"]
    limit = float(budget.monthly_limit_usd) if budget else 0.0
    decision = evaluate_policy(
        db,
        "quota",
        {"current_cost_usd": current},
        workspace_id=workspace_id,
    )
    pct = round(current / limit * 100, 1) if limit > 0 else 0
    return {
        "workspace_id": workspace_id,
        "current_usd": current,
        "monthly_limit_usd": limit,
        "utilization_pct": pct,
        "over_budget": limit > 0 and current > limit,
        "allowed": decision.allowed,
        "reason": decision.reason,
    }


def forecast_monthly(db: Session, workspace_id: int) -> dict[str, Any]:
    summary = workspace_cost_summary(db, workspace_id, days=7)
    daily_avg = summary["total_usd"] / 7 if summary["total_usd"] else 0
    forecast = round(daily_avg * 30, 4)
    return {
        "workspace_id": workspace_id,
        "daily_avg_usd": round(daily_avg, 6),
        "monthly_forecast_usd": forecast,
    }


def detect_cost_anomalies(db: Session, workspace_id: int) -> list[dict]:
    from app.database import CostLedger

    since = datetime.utcnow() - timedelta(days=1)
    rows = (
        db.query(CostLedger)
        .filter(CostLedger.workspace_id == workspace_id, CostLedger.create_time >= since)
        .order_by(CostLedger.amount_usd.desc())
        .limit(10)
        .all()
    )
    anomalies = []
    for r in rows:
        if float(r.amount_usd or 0) > 1.0:
            anomalies.append(
                {
                    "cost_type": r.cost_type,
                    "amount_usd": float(r.amount_usd),
                    "model": r.model,
                    "trace_id": r.trace_id,
                    "severity": "warning",
                }
            )
    return anomalies


def record_llm_cost_from_metrics(
    db: Session,
    *,
    workspace_id: int,
    organization_id: int | None,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    trace_id: str = "",
    resource_type: str = "ai_runtime",
    resource_id: str = "",
) -> float | None:
    cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
    if cost is None or cost <= 0:
        return cost
    record_cost(
        db,
        workspace_id=workspace_id,
        organization_id=organization_id,
        cost_type="llm",
        amount_usd=cost,
        trace_id=trace_id,
        model=model,
        resource_type=resource_type,
        resource_id=resource_id,
        meta={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    )
    return cost
