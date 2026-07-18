"""AgentOS verification engine."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.database import AgentVerificationReport


def verify_output(
    *,
    output: str,
    tool_results: list[dict] | None = None,
    knowledge_hits: list[dict] | None = None,
    policies: dict | None = None,
) -> dict[str, Any]:
    """Multi-source verification without bypassing KOS."""
    tool_results = tool_results or []
    knowledge_hits = knowledge_hits or []
    policies = policies or {}
    checks = []

    if tool_results:
        checks.append({"source": "tools", "status": "pass", "count": len(tool_results)})
    else:
        checks.append({"source": "tools", "status": "warn", "detail": "No tool evidence"})

    if knowledge_hits or any(t.get("tool") == "kb_search" for t in tool_results):
        checks.append({"source": "knowledge", "status": "pass"})
    else:
        checks.append({"source": "knowledge", "status": "skip"})

    math_claims = re.findall(r"\b\d+(?:\.\d+)?\s*[\+\-\*/]\s*\d+", output)
    if math_claims:
        checks.append({"source": "math", "status": "review", "claims": math_claims[:5]})

    if policies.get("require_citations") and not re.search(r"\[\d+\]", output):
        checks.append({"source": "citations", "status": "fail"})
    else:
        checks.append({"source": "citations", "status": "pass"})

    failed = [c for c in checks if c.get("status") == "fail"]
    verdict = "fail" if failed else ("pass" if all(c.get("status") != "warn" for c in checks) else "review")
    confidence = 0.85 if verdict == "pass" else (0.4 if verdict == "fail" else 0.65)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "checks": checks,
        "sources": [{"type": "tool", "count": len(tool_results)}, {"type": "knowledge", "count": len(knowledge_hits)}],
    }


def save_verification_report(
    db: Session,
    *,
    run_id: str,
    workspace_id: int,
    report: dict[str, Any],
) -> AgentVerificationReport:
    rec = AgentVerificationReport(
        id=uuid.uuid4().hex,
        run_id=run_id,
        workspace_id=workspace_id,
        verdict=report.get("verdict") or "pending",
        confidence=float(report.get("confidence") or 0),
        sources_json=json.dumps(report.get("sources") or []),
        report_json=json.dumps(report),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def report_dict(rec: AgentVerificationReport) -> dict[str, Any]:
    try:
        report = json.loads(rec.report_json or "{}")
    except json.JSONDecodeError:
        report = {}
    return {
        "id": rec.id,
        "run_id": rec.run_id,
        "verdict": rec.verdict,
        "confidence": rec.confidence,
        "report": report,
        "create_time": rec.create_time.isoformat() if rec.create_time else None,
    }
