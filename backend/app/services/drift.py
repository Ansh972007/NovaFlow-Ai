import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import EvalRun, EvalSuite


def _pass_rate(run: EvalRun) -> float:
    if not run.total_count:
        return 0.0
    return round(100.0 * run.pass_count / run.total_count, 1)


def _case_results(run: EvalRun) -> dict[str, dict]:
    try:
        payload = json.loads(run.results_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("case_id") or row.get("input") or len(out))
        out[key] = row
    return out


def compute_prompt_drift(
    db: Session,
    workspace_id: int,
    suite_id: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    q = db.query(EvalSuite).filter(EvalSuite.workspace_id == workspace_id)
    if suite_id:
        q = q.filter(EvalSuite.id == suite_id)
    suites = q.order_by(EvalSuite.update_time.desc()).limit(20).all()

    radar: list[dict] = []
    for suite in suites:
        runs = (
            db.query(EvalRun)
            .filter(EvalRun.suite_id == suite.id, EvalRun.workspace_id == workspace_id)
            .order_by(EvalRun.create_time.desc())
            .limit(limit)
            .all()
        )
        if len(runs) < 2:
            continue

        latest = runs[0]
        baseline = runs[min(len(runs) - 1, 5)]
        latest_rate = _pass_rate(latest)
        baseline_rate = _pass_rate(baseline)
        delta = round(latest_rate - baseline_rate, 1)

        latest_cases = _case_results(latest)
        baseline_cases = _case_results(baseline)
        regressions = []
        for key, row in latest_cases.items():
            prev = baseline_cases.get(key)
            if not prev:
                continue
            if prev.get("passed") and not row.get("passed"):
                regressions.append(
                    {
                        "case_id": row.get("case_id"),
                        "input": (row.get("input") or "")[:120],
                        "expected": (row.get("expected") or "")[:120],
                        "output": (row.get("output") or "")[:160],
                    }
                )

        severity = "stable"
        if delta <= -15 or len(regressions) >= 3:
            severity = "critical"
        elif delta <= -5 or regressions:
            severity = "warning"

        points = []
        for run in reversed(runs):
            points.append(
                {
                    "run_id": run.id,
                    "date": run.create_time.isoformat() if run.create_time else None,
                    "pass_rate": _pass_rate(run),
                }
            )

        radar.append(
            {
                "suite_id": suite.id,
                "suite_name": suite.name,
                "latest_run_id": latest.id,
                "baseline_run_id": baseline.id,
                "pass_rate": latest_rate,
                "baseline_pass_rate": baseline_rate,
                "delta": delta,
                "severity": severity,
                "regression_count": len(regressions),
                "regressions": regressions[:5],
                "points": points,
            }
        )

    radar.sort(key=lambda r: (r["severity"] != "critical", r["severity"] != "warning", r["delta"]))
    return {
        "suites_analyzed": len(radar),
        "critical_count": sum(1 for r in radar if r["severity"] == "critical"),
        "warning_count": sum(1 for r in radar if r["severity"] == "warning"),
        "radar": radar,
    }
