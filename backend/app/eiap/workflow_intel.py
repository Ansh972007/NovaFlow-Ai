"""EIAP workflow intelligence — analyze execution history, recommend optimizations.

Reuses workflow_intelligence.observability. Never re-implements workflow execution.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.eiap.recommendations import create_recommendation
from app.workflow_intelligence.observability import workspace_run_stats


def analyze_workflows(db: Session, *, workspace_id: int, limit: int = 200) -> dict[str, Any]:
    from app.database import Workflow, WorkflowRun

    stats = workspace_run_stats(db, workspace_id, limit=limit)
    workflows = db.query(Workflow).filter(Workflow.workspace_id == workspace_id).all()

    per_workflow: list[dict[str, Any]] = []
    worst: list[dict[str, Any]] = []
    for wf in workflows:
        runs = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.workspace_id == workspace_id, WorkflowRun.workflow_id == wf.id)
            .order_by(WorkflowRun.create_time.desc())
            .limit(50)
            .all()
        )
        total = len(runs)
        if not total:
            continue
        errors = sum(1 for r in runs if int(r.status or 1) == 2)
        durations = [int(r.duration_ms or 0) for r in runs if r.duration_ms]
        avg_ms = round(sum(durations) / len(durations), 1) if durations else 0
        entry = {
            "workflow_id": wf.id,
            "name": wf.name,
            "runs": total,
            "failure_rate": round(errors / total, 3),
            "avg_duration_ms": avg_ms,
        }
        per_workflow.append(entry)
        if entry["failure_rate"] >= 0.3 or avg_ms > 20000:
            worst.append(entry)

    per_workflow.sort(key=lambda e: (-e["failure_rate"], -e["avg_duration_ms"]))
    return {
        "workspace_id": workspace_id,
        "summary": stats,
        "workflows": per_workflow,
        "attention": worst,
    }


def recommend(db: Session, *, workspace_id: int, organization_id: int | None = None) -> list[dict[str, Any]]:
    analysis = analyze_workflows(db, workspace_id=workspace_id)
    created: list[dict[str, Any]] = []
    for wf in analysis["attention"]:
        if wf["failure_rate"] >= 0.3:
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="workflow",
                category="reliability",
                severity="high" if wf["failure_rate"] >= 0.5 else "medium",
                title=f"High failure rate in workflow '{wf['name']}'",
                detail=f"{int(wf['failure_rate'] * 100)}% of recent runs failed. Review node error handling, add retries, or replace unreliable nodes.",
                resource_type="workflow",
                resource_id=wf["workflow_id"],
                evidence=wf,
                estimated_impact="Improved reliability and fewer failed executions",
            )
            created.append({"id": rec.id, "title": rec.title})
        if wf["avg_duration_ms"] > 20000:
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="workflow",
                category="latency",
                severity="medium",
                title=f"Slow workflow '{wf['name']}'",
                detail="Average duration exceeds 20s. Consider parallelizing independent nodes, caching retrieval, or switching to a faster model.",
                resource_type="workflow",
                resource_id=wf["workflow_id"],
                evidence=wf,
                estimated_impact="Lower latency and cost per run",
            )
            created.append({"id": rec.id, "title": rec.title})
    return created
