"""Migration health reports — pre/post checks for zero-downtime upgrades."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.data.dialect import detect_dialect, dialect_capabilities
from app.data.partitioning import ensure_monthly_partitions


def schema_inventory(engine: Engine) -> dict[str, Any]:
    insp = inspect(engine)
    tables = sorted(insp.get_table_names())
    detail = {}
    for t in tables:
        cols = [c["name"] for c in insp.get_columns(t)]
        idxs = [i["name"] for i in insp.get_indexes(t)]
        detail[t] = {"columns": cols, "indexes": idxs}
    return {"table_count": len(tables), "tables": detail}


def verify_tenant_columns(engine: Engine, required: tuple[str, ...] = ("workspace_id",)) -> dict:
    """Check critical resource tables expose tenant columns."""
    targets = (
        "assistants",
        "knowledge",
        "workflows",
        "workflow_runs",
        "usage_events",
        "saved_agents",
        "eval_suites",
        "eval_runs",
        "api_keys",
        "dev_projects",
    )
    insp = inspect(engine)
    missing: dict[str, list[str]] = {}
    present = []
    for t in targets:
        if t not in insp.get_table_names():
            # knowledge table may be named knowledge_bases
            alt = "knowledge_bases" if t == "knowledge" else None
            if alt and alt in insp.get_table_names():
                t = alt
            else:
                continue
        cols = {c["name"] for c in insp.get_columns(t)}
        miss = [c for c in required if c not in cols]
        if miss:
            missing[t] = miss
        else:
            present.append(t)
    return {"ok": not missing, "present": present, "missing": missing}


def migration_impact_report(engine: Engine) -> dict:
    kind = detect_dialect(str(engine.url))
    caps = dialect_capabilities(kind)
    inventory = schema_inventory(engine)
    tenant = verify_tenant_columns(engine)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "dialect": kind.value,
        "capabilities": caps,
        "estimated_downtime": "online (expand/contract) — seconds for additive columns; minutes for partition parent cutover",
        "rollback_strategy": "alembic downgrade -1; additive columns are nullable and backward compatible",
        "tenant_check": tenant,
        "table_count": inventory["table_count"],
        "compatibility": {
            "api": "unchanged",
            "platform_context": "unchanged",
            "security": "unchanged",
        },
    }


def post_migration_verify(engine: Engine) -> dict:
    kind = detect_dialect(str(engine.url))
    checks = {
        "ping": False,
        "tenant_columns": False,
        "partitions": None,
    }
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["ping"] = True
    except Exception as exc:
        checks["ping_error"] = str(exc)
    tenant = verify_tenant_columns(engine)
    checks["tenant_columns"] = tenant["ok"]
    checks["tenant_detail"] = tenant
    if kind.value == "postgresql":
        checks["partitions"] = ensure_monthly_partitions(engine)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ok": checks["ping"] and checks["tenant_columns"],
        "checks": checks,
    }


def write_report(path: str, report: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
