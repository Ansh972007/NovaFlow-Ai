"""EIAP FinOps intelligence — cost optimization recommendations.

Reuses platform_intelligence.finops.ledger. Never re-implements cost tracking.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.eiap.model_intel import benchmark_models
from app.eiap.recommendations import create_recommendation
from app.platform_intelligence.finops.ledger import (
    detect_cost_anomalies,
    forecast_monthly,
    workspace_cost_summary,
)


def cost_analysis(db: Session, *, workspace_id: int, days: int = 30) -> dict[str, Any]:
    summary = workspace_cost_summary(db, workspace_id, days=days)
    forecast = forecast_monthly(db, workspace_id)
    anomalies = detect_cost_anomalies(db, workspace_id)
    models = benchmark_models(db, workspace_id=workspace_id, days=days)
    return {
        "workspace_id": workspace_id,
        "summary": summary,
        "forecast": forecast,
        "anomalies": anomalies,
        "model_costs": models["benchmarks"],
    }


def recommend(db: Session, *, workspace_id: int, organization_id: int | None = None) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    analysis = cost_analysis(db, workspace_id=workspace_id)

    anomalies = analysis["anomalies"]
    if anomalies:
        rec = create_recommendation(
            db,
            workspace_id=workspace_id,
            organization_id=organization_id,
            domain="finops",
            category="anomaly",
            severity="high",
            title=f"{len(anomalies)} cost anomalies detected",
            detail="High-cost operations detected in the last 24h. Review the largest spends and consider caching or cheaper models.",
            resource_type="cost",
            evidence={"anomalies": anomalies},
            estimated_impact="Reduced runaway spend",
        )
        created.append({"id": rec.id, "title": rec.title})

    benchmarks = [b for b in analysis["model_costs"] if b["calls"] >= 5]
    if len(benchmarks) >= 2:
        cheapest = min(benchmarks, key=lambda b: b["avg_cost_per_call"])
        priciest = max(benchmarks, key=lambda b: b["avg_cost_per_call"])
        if priciest["avg_cost_per_call"] > cheapest["avg_cost_per_call"] * 3 and priciest["error_rate"] <= cheapest["error_rate"] + 0.05:
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="finops",
                category="model_swap",
                severity="medium",
                title=f"Consider switching from {priciest['model']} to {cheapest['model']}",
                detail=f"{priciest['model']} costs ${priciest['avg_cost_per_call']:.5f}/call vs ${cheapest['avg_cost_per_call']:.5f} for {cheapest['model']} with comparable reliability.",
                resource_type="model",
                resource_id=priciest["model"],
                evidence={"cheapest": cheapest, "priciest": priciest},
                estimated_impact="Lower LLM spend at similar quality",
            )
            created.append({"id": rec.id, "title": rec.title})
    return created
