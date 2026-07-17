"""SQLAlchemy mixins — tenant columns, soft delete, optimistic locking, timestamps.

New models SHOULD inherit these. Existing models gain columns via Alembic
migration 0002 without requiring class rewrite in the same commit.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String


class TimestampMixin:
    create_time = Column(DateTime, default=datetime.utcnow, index=True)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True, index=True)
    legal_hold = Column(Integer, default=0)  # 1 = cannot purge


class TenantMixin:
    """Standard multi-tenant columns for workspace-scoped resources."""

    workspace_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    team_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(Integer, nullable=True, index=True)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    visibility = Column(String(16), default="workspace")
    tenant_version = Column(Integer, default=1)


class OptimisticLockMixin:
    """Increment on each update; compare before commit for conflict detection."""

    row_version = Column(Integer, default=1, nullable=False)


# Recommended composite index names (documented for Alembic / DBA review)
TENANT_INDEX_SPECS = (
    # (table_hint, columns, notes)
    ("*", ("workspace_id", "deleted_at"), "tenant + soft-delete filter"),
    ("*", ("workspace_id", "create_time"), "tenant time-series"),
    ("*", ("workspace_id", "owner_id"), "ownership queries"),
    ("security_audit_logs", ("workspace_id", "created_at"), "audit BRIN/BTREE"),
    ("workflow_runs", ("workspace_id", "create_time"), "execution history"),
    ("usage_events", ("workspace_id", "create_time"), "analytics"),
)
