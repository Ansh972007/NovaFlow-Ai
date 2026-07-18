"""EIAP reporting — daily/weekly/monthly/executive report generation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import EIAPReport
from app.eiap.finops import cost_analysis
from app.eiap.governance import workspace_health_report
from app.eiap.observability import unified_health


def generate_report(
    db: Session,
    *,
    workspace_id: int,
    report_type: str = "daily",
    organization_id: int | None = None,
) -> dict[str, Any]:
    health = unified_health(db, workspace_id=workspace_id)
    governance = workspace_health_report(db, workspace_id=workspace_id)
    cost = cost_analysis(db, workspace_id=workspace_id)

    payload = {
        "report_type": report_type,
        "generated_at": datetime.utcnow().isoformat(),
        "health": health,
        "governance": {
            "open_recommendations": governance["open_recommendations"],
            "critical_recommendations": governance["critical_recommendations"],
            "posture": governance["posture"],
        },
        "cost": {
            "total_30d_usd": cost["summary"].get("total_usd"),
            "monthly_forecast_usd": cost["forecast"].get("monthly_forecast_usd"),
            "anomalies": len(cost["anomalies"]),
        },
    }
    summary = _summarize(payload)

    rec = EIAPReport(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        organization_id=organization_id,
        report_type=report_type,
        period=datetime.utcnow().strftime("%Y-%m-%d"),
        payload_json=json.dumps(payload),
        summary=summary,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "report_type": report_type, "summary": summary, "payload": payload}


def _summarize(payload: dict) -> str:
    health = payload["health"]
    gov = payload["governance"]
    cost = payload["cost"]
    return (
        f"System health: {health['status']} ({health['overall_health_score']}). "
        f"{gov['open_recommendations']} open recommendations ({gov['critical_recommendations']} critical). "
        f"30d cost ${cost['total_30d_usd'] or 0}, forecast ${cost['monthly_forecast_usd'] or 0}."
    )


def list_reports(db: Session, *, workspace_id: int, report_type: str = "", limit: int = 30) -> list[dict[str, Any]]:
    q = db.query(EIAPReport).filter(EIAPReport.workspace_id == workspace_id)
    if report_type:
        q = q.filter(EIAPReport.report_type == report_type)
    rows = q.order_by(EIAPReport.create_time.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "report_type": r.report_type,
            "period": r.period,
            "summary": r.summary,
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in rows
    ]
