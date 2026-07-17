"""PostgreSQL partitioning helpers — monthly RANGE on created_at / create_time.

SQLite/MySQL: no-op (capability gate). Automatic partition creation for N months ahead.
"""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.data.config import load_data_config
from app.data.dialect import DialectKind, detect_dialect

logger = logging.getLogger("novaflow.data.partitioning")

# Logical parent tables → time column (PostgreSQL PARTITION BY RANGE)
PARTITIONED_TABLES: dict[str, str] = {
    "security_audit_logs_p": "created_at",
    "workflow_runs_p": "create_time",
    "usage_events_p": "create_time",
    "notifications_p": "create_time",
}


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def iter_months_ahead(n: int, *, from_date: date | None = None) -> Iterable[tuple[int, int]]:
    d = from_date or date.today().replace(day=1)
    y, m = d.year, d.month
    for _ in range(max(0, n) + 1):  # current + ahead
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def ensure_monthly_partitions(engine: Engine, *, months_ahead: int | None = None) -> dict:
    """Create missing monthly partitions for registered parent tables (PostgreSQL only)."""
    cfg = load_data_config()
    kind = detect_dialect(cfg.database_url)
    report = {"dialect": kind.value, "created": [], "skipped": [], "errors": []}
    if kind != DialectKind.POSTGRESQL:
        report["skipped"].append("partitioning requires postgresql")
        return report

    ahead = months_ahead if months_ahead is not None else cfg.partition_months_ahead
    with engine.begin() as conn:
        for parent, col in PARTITIONED_TABLES.items():
            exists = conn.execute(
                text("SELECT to_regclass(:name) IS NOT NULL"),
                {"name": parent},
            ).scalar()
            if not exists:
                report["skipped"].append(f"{parent}: parent table not present yet")
                continue
            for y, m in iter_months_ahead(ahead):
                part = f"{parent}_{y}_{m:02d}"
                start, end = month_bounds(y, m)
                try:
                    conn.execute(
                        text(
                            f"""
                            CREATE TABLE IF NOT EXISTS {part}
                            PARTITION OF {parent}
                            FOR VALUES FROM (:start) TO (:end)
                            """
                        ),
                        {"start": start.isoformat(), "end": end.isoformat()},
                    )
                    report["created"].append(part)
                except Exception as exc:
                    # already exists or race
                    msg = str(exc)
                    if "already exists" in msg.lower():
                        report["skipped"].append(part)
                    else:
                        report["errors"].append(f"{part}: {msg}")
                        logger.warning("Partition create failed %s: %s", part, exc)
    return report


def postgres_partition_ddl_templates() -> dict[str, str]:
    """Documented DDL for creating partitioned parents (applied by Alembic on PG)."""
    return {
        "security_audit_logs_p": """
CREATE TABLE IF NOT EXISTS security_audit_logs_p (
    id BIGSERIAL,
    action VARCHAR(120) NOT NULL,
    actor_user_id INTEGER,
    workspace_id INTEGER,
    resource_type VARCHAR(64) DEFAULT '',
    resource_id VARCHAR(128) DEFAULT '',
    ip_address VARCHAR(64) DEFAULT '',
    user_agent VARCHAR(512) DEFAULT '',
    success INTEGER DEFAULT 1,
    detail_json TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
CREATE INDEX IF NOT EXISTS ix_sal_p_ws_created ON security_audit_logs_p (workspace_id, created_at);
""",
        "workflow_runs_p": """
CREATE TABLE IF NOT EXISTS workflow_runs_p (
    id BIGSERIAL,
    workflow_id VARCHAR(32),
    user_id INTEGER,
    workspace_id INTEGER,
    input_text TEXT,
    output_text TEXT,
    steps_json TEXT,
    status VARCHAR(32),
    duration_ms INTEGER,
    create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, create_time)
) PARTITION BY RANGE (create_time);
CREATE INDEX IF NOT EXISTS ix_wr_p_ws_time ON workflow_runs_p (workspace_id, create_time);
""",
    }
