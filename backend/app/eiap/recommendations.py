"""EIAP recommendation store — approval-gated, never auto-applied."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import EIAPRecommendation

VALID_DOMAINS = {"workflow", "agent", "knowledge", "connectivity", "model", "finops", "prompt", "search", "governance"}


def recommendation_dict(rec: EIAPRecommendation) -> dict[str, Any]:
    try:
        evidence = json.loads(rec.evidence_json or "{}")
    except json.JSONDecodeError:
        evidence = {}
    return {
        "id": rec.id,
        "domain": rec.domain,
        "category": rec.category,
        "severity": rec.severity,
        "title": rec.title,
        "detail": rec.detail,
        "resource_type": rec.resource_type,
        "resource_id": rec.resource_id,
        "evidence": evidence,
        "estimated_impact": rec.estimated_impact,
        "status": rec.status,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        "create_time": rec.create_time.isoformat() if rec.create_time else None,
    }


def create_recommendation(
    db: Session,
    *,
    workspace_id: int,
    domain: str,
    title: str,
    detail: str = "",
    category: str = "optimization",
    severity: str = "info",
    resource_type: str = "",
    resource_id: str = "",
    evidence: dict | None = None,
    estimated_impact: str = "",
    organization_id: int | None = None,
    trace_id: str = "",
    dedupe: bool = True,
) -> EIAPRecommendation:
    domain = domain if domain in VALID_DOMAINS else "workflow"
    if dedupe:
        existing = (
            db.query(EIAPRecommendation)
            .filter(
                EIAPRecommendation.workspace_id == workspace_id,
                EIAPRecommendation.domain == domain,
                EIAPRecommendation.title == title[:200],
                EIAPRecommendation.status == "open",
            )
            .first()
        )
        if existing:
            return existing
    rec = EIAPRecommendation(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        organization_id=organization_id,
        domain=domain,
        category=category,
        severity=severity,
        title=title[:200],
        detail=detail,
        resource_type=resource_type,
        resource_id=str(resource_id or ""),
        evidence_json=json.dumps(evidence or {}),
        estimated_impact=estimated_impact[:200],
        status="open",
        trace_id=trace_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_recommendations(
    db: Session,
    *,
    workspace_id: int,
    domain: str = "",
    status: str = "",
    limit: int = 100,
) -> list[EIAPRecommendation]:
    q = db.query(EIAPRecommendation).filter(EIAPRecommendation.workspace_id == workspace_id)
    if domain:
        q = q.filter(EIAPRecommendation.domain == domain)
    if status:
        q = q.filter(EIAPRecommendation.status == status)
    return q.order_by(EIAPRecommendation.create_time.desc()).limit(limit).all()


def get_recommendation(db: Session, rec_id: str, *, workspace_id: int) -> EIAPRecommendation | None:
    rec = db.get(EIAPRecommendation, rec_id)
    if not rec or rec.workspace_id != workspace_id:
        return None
    return rec


def set_status(
    db: Session,
    rec: EIAPRecommendation,
    *,
    status: str,
    reviewed_by: int | None = None,
) -> EIAPRecommendation:
    if status not in ("open", "approved", "applied", "dismissed"):
        raise ValueError("Invalid status")
    rec.status = status
    rec.reviewed_by = reviewed_by
    rec.reviewed_at = datetime.utcnow()
    rec.update_time = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec
