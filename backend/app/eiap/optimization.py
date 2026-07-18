"""EIAP autonomous optimization engine.

Generates recommendations across all domains. NEVER applies changes automatically —
every recommendation requires explicit approval before it can be acted upon.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.eiap import agent_intel, connectivity_intel, finops, knowledge_intel, workflow_intel


def run_optimization_scan(
    db: Session,
    *,
    workspace_id: int,
    organization_id: int | None = None,
    domains: list[str] | None = None,
) -> dict[str, Any]:
    """Scan all (or selected) domains and persist open recommendations.

    Recommendations are advisory only and default to status='open' pending approval.
    """
    domains = domains or ["workflow", "agent", "knowledge", "connectivity", "finops"]
    results: dict[str, list] = {}

    if "workflow" in domains:
        results["workflow"] = workflow_intel.recommend(db, workspace_id=workspace_id, organization_id=organization_id)
    if "agent" in domains:
        results["agent"] = agent_intel.recommend(db, workspace_id=workspace_id, organization_id=organization_id)
    if "knowledge" in domains:
        results["knowledge"] = knowledge_intel.recommend(db, workspace_id=workspace_id, organization_id=organization_id)
    if "connectivity" in domains:
        results["connectivity"] = connectivity_intel.recommend(db, workspace_id=workspace_id, organization_id=organization_id)
    if "finops" in domains:
        results["finops"] = finops.recommend(db, workspace_id=workspace_id, organization_id=organization_id)

    total = sum(len(v) for v in results.values())

    try:
        from app.platform_intelligence.events.emitter import emit_platform_event

        emit_platform_event(
            db,
            "EIAPOptimizationScan",
            workspace_id=workspace_id,
            organization_id=organization_id,
            resource_type="eiap",
            resource_id="optimization",
            payload={"domains": domains, "recommendations": total},
        )
    except Exception:
        pass

    return {
        "workspace_id": workspace_id,
        "domains": domains,
        "recommendations_created": total,
        "by_domain": {k: len(v) for k, v in results.items()},
        "note": "All recommendations require approval. Nothing is applied automatically.",
    }
