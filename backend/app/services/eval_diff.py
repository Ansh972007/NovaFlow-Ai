import json
from typing import Any

from app.database import EvalRun


def _extract_results(run: EvalRun) -> list[dict[str, Any]]:
    try:
        payload = json.loads(run.results_json or "[]")
    except json.JSONDecodeError:
        payload = []
    if isinstance(payload, dict):
        return payload.get("results", [])
    return payload if isinstance(payload, list) else []


def diff_eval_runs(current: EvalRun, baseline: EvalRun) -> dict:
    cur_map = {r.get("case_id"): r for r in _extract_results(current) if r.get("case_id") is not None}
    base_map = {r.get("case_id"): r for r in _extract_results(baseline) if r.get("case_id") is not None}
    case_ids = sorted(set(cur_map) | set(base_map))

    items: list[dict[str, Any]] = []
    counts = {"regressed": 0, "improved": 0, "unchanged": 0, "new": 0, "removed": 0}

    for case_id in case_ids:
        cur = cur_map.get(case_id)
        base = base_map.get(case_id)

        if cur and not base:
            status = "new"
            counts["new"] += 1
        elif base and not cur:
            status = "removed"
            counts["removed"] += 1
        else:
            cur_pass = bool(cur.get("passed"))
            base_pass = bool(base.get("passed"))
            if cur_pass and not base_pass:
                status = "improved"
                counts["improved"] += 1
            elif not cur_pass and base_pass:
                status = "regressed"
                counts["regressed"] += 1
            else:
                status = "unchanged"
                counts["unchanged"] += 1

        items.append(
            {
                "case_id": case_id,
                "status": status,
                "input": (cur or base or {}).get("input", ""),
                "expected": (cur or base or {}).get("expected", ""),
                "current": {
                    "passed": cur.get("passed") if cur else None,
                    "output": (cur.get("output") or "")[:500] if cur else None,
                    "latency_ms": cur.get("latency_ms") if cur else None,
                },
                "baseline": {
                    "passed": base.get("passed") if base else None,
                    "output": (base.get("output") or "")[:500] if base else None,
                    "latency_ms": base.get("latency_ms") if base else None,
                },
            }
        )

    cur_rate = round((current.pass_count / current.total_count) * 100, 1) if current.total_count else 0
    base_rate = round((baseline.pass_count / baseline.total_count) * 100, 1) if baseline.total_count else 0

    return {
        "current_run_id": current.id,
        "baseline_run_id": baseline.id,
        "current_pass_rate": cur_rate,
        "baseline_pass_rate": base_rate,
        "pass_rate_delta": round(cur_rate - base_rate, 1),
        "summary": counts,
        "items": items,
    }
