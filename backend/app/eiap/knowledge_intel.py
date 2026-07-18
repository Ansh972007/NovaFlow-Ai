"""EIAP knowledge intelligence — detect stale/duplicate/weak collections.

Reuses knowledge_os.curator. Never re-implements retrieval or indexing.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.eiap.recommendations import create_recommendation
from app.knowledge_os.curator import analyze_collection, workspace_analytics


def analyze_knowledge(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.database import KnowledgeBase

    overview = workspace_analytics(db, workspace_id=workspace_id)
    collections = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id).all()
    reports = []
    for kb in collections:
        report = analyze_collection(db, kb)
        reports.append(report)
    reports.sort(key=lambda r: r.get("score", 1.0))
    return {
        "workspace_id": workspace_id,
        "overview": overview,
        "collection_health": reports,
    }


def recommend(db: Session, *, workspace_id: int, organization_id: int | None = None) -> list[dict[str, Any]]:
    from app.database import KnowledgeBase

    created: list[dict[str, Any]] = []
    collections = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id).all()
    for kb in collections:
        report = analyze_collection(db, kb)
        for r in report.get("recommendations", []):
            action = r.get("action", "review")
            severity = "high" if action in ("reindex", "delete") else "low"
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="knowledge",
                category=action,
                severity=severity,
                title=f"{action.title()} collection '{kb.name}'",
                detail=r.get("reason", ""),
                resource_type="knowledge",
                resource_id=str(kb.id),
                evidence={"health_score": report.get("score"), **r},
                estimated_impact="Improved retrieval quality and reduced storage waste",
            )
            created.append({"id": rec.id, "title": rec.title})
    return created
