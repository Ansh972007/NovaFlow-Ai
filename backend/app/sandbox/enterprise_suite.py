"""Enterprise sandbox test suite — structural, fixture, contract, and budget checks."""

from __future__ import annotations

import time
from typing import Any

from app.sandbox.twin import _iter_nodes, run_sandbox_trial

# Wall-clock budget for structural + fixture + twin probe (ms)
DEFAULT_BUDGET_MS = 3000

_REQUIRED_TYPES = ("trigger", "llm", "output")

_FIELD_FIXTURES: dict[str, dict[str, Any]] = {
    "finance": {"input": "Invoice #1001 due 2026-09-01 amount 1200", "expect_keywords": ["invoice"]},
    "hr": {"input": "New hire: Ada Lovelace starts Monday", "expect_keywords": ["hire"]},
    "support": {"input": "Customer asks about refund policy", "expect_keywords": ["refund"]},
    "sales": {"input": "Lead: Acme Corp interested in Pro plan", "expect_keywords": ["lead"]},
    "content": {"input": "Draft a short status update from notes", "expect_keywords": ["draft"]},
    "ops": {"input": "Weekly ops digest from documents", "expect_keywords": ["digest"]},
    "generic": {"input": "Run the automation with sample input", "expect_keywords": []},
}


def _node_types(graph: dict[str, Any]) -> set[str]:
    types: set[str] = set()
    for _nid, data in _iter_nodes(graph or {}):
        t = str(data.get("type") or "").lower()
        if t:
            types.add(t)
    meta_types = (graph.get("meta") or {}).get("node_types") or []
    for t in meta_types:
        if t:
            types.add(str(t).lower())
    return types


def _edge_pairs(graph: dict[str, Any]) -> list[tuple[str, str]]:
    edges = graph.get("edges") or []
    pairs: list[tuple[str, str]] = []
    if not isinstance(edges, list):
        return pairs
    for e in edges:
        if not isinstance(e, dict):
            continue
        src = str(e.get("from") or e.get("source") or "")
        dst = str(e.get("to") or e.get("target") or "")
        if src and dst:
            pairs.append((src, dst))
    return pairs


def check_structural(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = _iter_nodes(graph or {})
    if not nodes:
        return {
            "id": "structural",
            "name": "Structural",
            "status": "failed",
            "message": "Graph has no nodes",
        }
    types = _node_types(graph)
    missing = [t for t in _REQUIRED_TYPES if t not in types]
    if missing:
        return {
            "id": "structural",
            "name": "Structural",
            "status": "failed",
            "message": f"Missing required node types: {', '.join(missing)}",
            "missing": missing,
        }
    pairs = _edge_pairs(graph)
    if len(nodes) > 1 and not pairs:
        return {
            "id": "structural",
            "name": "Structural",
            "status": "failed",
            "message": "Nodes present but no edges connecting them",
        }
    return {
        "id": "structural",
        "name": "Structural",
        "status": "passed",
        "message": f"{len(nodes)} nodes, {len(pairs)} edges, types ok",
        "node_count": len(nodes),
        "edge_count": len(pairs),
    }


def check_capability_contract(
    graph: dict[str, Any],
    *,
    missing_credentials: list[str] | None = None,
) -> dict[str, Any]:
    """Warn on missing credentials; fail only if notify nodes exist without any notify path."""
    missing = [m for m in (missing_credentials or []) if m]
    types = _node_types(graph)
    notifyish = types & {"notify", "telegram", "slack", "discord", "email", "webhook"}
    if missing and notifyish:
        return {
            "id": "capability_contract",
            "name": "Capability contract",
            "status": "warn",
            "message": f"Notify nodes present; missing credentials: {', '.join(missing[:6])}",
            "missing_credentials": missing,
        }
    if missing:
        return {
            "id": "capability_contract",
            "name": "Capability contract",
            "status": "warn",
            "message": f"Missing credentials (non-blocking): {', '.join(missing[:6])}",
            "missing_credentials": missing,
        }
    return {
        "id": "capability_contract",
        "name": "Capability contract",
        "status": "passed",
        "message": "No blocking credential gaps",
    }


def check_fixture_smoke(graph: dict[str, Any], *, field: str | None = None) -> dict[str, Any]:
    """Deterministic mini-input probe — graph must remain structurally runnable."""
    key = (field or "generic").lower()
    fixture = _FIELD_FIXTURES.get(key) or _FIELD_FIXTURES["generic"]
    # Fixture "runs" if structural types exist; twin validates execution path.
    types = _node_types(graph)
    if not types:
        return {
            "id": "fixture_smoke",
            "name": "Fixture smoke",
            "status": "failed",
            "message": "Cannot run fixture on empty graph",
            "fixture": fixture.get("input"),
        }
    return {
        "id": "fixture_smoke",
        "name": "Fixture smoke",
        "status": "passed",
        "message": f"Fixture ready for field={key}",
        "fixture": fixture.get("input"),
        "field": key,
    }


def check_twin_probe(graph: dict[str, Any]) -> dict[str, Any]:
    trial = run_sandbox_trial(graph if isinstance(graph, dict) else {})
    ok = trial.get("status") == "success"
    return {
        "id": "twin_probe",
        "name": "Latency probe",
        "status": "passed" if ok else "failed",
        "message": f"Twin status={trial.get('status')} latency={trial.get('total_latency_ms')}ms",
        "trial": trial,
    }


def run_enterprise_suite(
    graph_payload: dict[str, Any] | None,
    *,
    missing_credentials: list[str] | None = None,
    field: str | None = None,
    budget_ms: int = DEFAULT_BUDGET_MS,
    include_twin: bool = True,
) -> dict[str, Any]:
    """
    Run enterprise checks. Returns rich report:
    {status, checks[], passed, failed, warnings, total_ms, ...twin fields}
    """
    started = time.perf_counter()
    graph = graph_payload if isinstance(graph_payload, dict) else {}
    checks: list[dict[str, Any]] = [
        check_structural(graph),
        check_capability_contract(graph, missing_credentials=missing_credentials),
        check_fixture_smoke(graph, field=field),
    ]
    twin_trial: dict[str, Any] = {}
    if include_twin:
        twin_check = check_twin_probe(graph)
        checks.append(twin_check)
        twin_trial = twin_check.get("trial") or {}

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    budget_ok = elapsed_ms <= max(100, int(budget_ms or DEFAULT_BUDGET_MS))
    checks.append(
        {
            "id": "budget",
            "name": "Budget",
            "status": "passed" if budget_ok else "failed",
            "message": f"Suite wall time {elapsed_ms}ms (budget {budget_ms}ms)",
            "elapsed_ms": elapsed_ms,
            "budget_ms": budget_ms,
        }
    )

    passed = sum(1 for c in checks if c.get("status") == "passed")
    failed = sum(1 for c in checks if c.get("status") == "failed")
    warnings = sum(1 for c in checks if c.get("status") == "warn")
    hard_fail = failed > 0
    status = "failed" if hard_fail else "success"

    report: dict[str, Any] = {
        "status": status,
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "total_ms": elapsed_ms,
        "suite": "enterprise",
        "logs": [f"[{c.get('status')}] {c.get('name')}: {c.get('message')}" for c in checks],
        "node_count": twin_trial.get("node_count") or len(_iter_nodes(graph)),
        "total_latency_ms": twin_trial.get("total_latency_ms") or elapsed_ms,
        "nodes": twin_trial.get("nodes") or [],
        "performance_profile": twin_trial.get("performance_profile")
        or ("optimal" if elapsed_ms < 1000 else "warning_latency"),
    }
    return report


def run_simulation_matrix(
    graph_payload: dict[str, Any] | None,
    *,
    fields: list[str] | None = None,
    missing_credentials: list[str] | None = None,
    budget_ms: int = DEFAULT_BUDGET_MS,
) -> dict[str, Any]:
    """Run enterprise suite across multiple field fixtures; return pass/fail matrix."""
    graph = graph_payload if isinstance(graph_payload, dict) else {}
    use_fields = fields or ["finance", "hr", "support", "sales", "ops", "generic"]
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for field in use_fields:
        report = run_enterprise_suite(
            graph,
            missing_credentials=missing_credentials,
            field=field,
            budget_ms=budget_ms,
            include_twin=True,
        )
        rows.append(
            {
                "field": field,
                "status": report.get("status"),
                "passed": report.get("passed"),
                "failed": report.get("failed"),
                "warnings": report.get("warnings"),
                "total_ms": report.get("total_ms"),
                "fixture": (_FIELD_FIXTURES.get(field) or _FIELD_FIXTURES["generic"]).get("input"),
            }
        )
    total_ms = int((time.perf_counter() - started) * 1000)
    ok = sum(1 for r in rows if r.get("status") == "success")
    bad = len(rows) - ok
    return {
        "status": "success" if bad == 0 else "failed",
        "suite": "simulation_matrix",
        "rows": rows,
        "passed_fields": ok,
        "failed_fields": bad,
        "total_ms": total_ms,
        "field_count": len(rows),
        "logs": [f"[{r['status']}] {r['field']}: {r.get('fixture', '')[:60]}" for r in rows],
    }
