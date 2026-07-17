"""Enterprise Data Platform — soft-delete columns, object_files, tenant indexes, PG partitions.

Revision ID: 0002_enterprise_data_platform
Revises: 0001_security_foundation

Online / expand-contract safe:
- Additive nullable columns only on live tables
- Partitioned parents are new tables (dual-write cutover later)
- Downgrade drops only what this revision creates
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_enterprise_data_platform"
down_revision: Union[str, None] = "0001_security_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENTERPRISE_TABLES = (
    "assistants",
    "knowledge_bases",
    "workflows",
    "workflow_runs",
    "saved_agents",
    "eval_suites",
    "eval_runs",
    "dev_projects",
    "api_keys",
)

ENTERPRISE_COLUMNS = (
    ("deleted_at", sa.DateTime(), True),
    ("legal_hold", sa.Integer(), False),
    ("row_version", sa.Integer(), False),
    ("visibility", sa.String(16), False),
    ("organization_id", sa.Integer(), True),
    ("team_id", sa.Integer(), True),
    ("owner_id", sa.Integer(), True),
    ("created_by", sa.Integer(), True),
    ("updated_by", sa.Integer(), True),
    ("tenant_version", sa.Integer(), False),
)


def _dialect() -> str:
    return op.get_bind().dialect.name


def _add_column_if_missing(table: str, name: str, col: sa.Column) -> None:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if name in existing:
        return
    op.add_column(table, col)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())

    for table in ENTERPRISE_TABLES:
        if table not in tables:
            continue
        for name, typ, nullable in ENTERPRISE_COLUMNS:
            kwargs = {"nullable": nullable}
            if name == "legal_hold":
                kwargs["server_default"] = "0"
            elif name == "row_version":
                kwargs["server_default"] = "1"
            elif name == "visibility":
                kwargs["server_default"] = "workspace"
            elif name == "tenant_version":
                kwargs["server_default"] = "1"
            _add_column_if_missing(table, name, sa.Column(name, typ, **kwargs))

        # Tenant composite indexes (skip if already present)
        idx_name = f"ix_{table}_ws_deleted"
        existing_idx = {i["name"] for i in insp.get_indexes(table)}
        if idx_name not in existing_idx and "workspace_id" in {
            c["name"] for c in insp.get_columns(table)
        }:
            try:
                op.create_index(idx_name, table, ["workspace_id", "deleted_at"])
            except Exception:
                pass

    if "object_files" not in tables:
        op.create_table(
            "object_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("workspace_id", sa.Integer(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("visibility", sa.String(16), server_default="workspace"),
            sa.Column("tenant_version", sa.Integer(), server_default="1"),
            sa.Column("storage_key", sa.String(512), nullable=False),
            sa.Column("bucket", sa.String(128), server_default=""),
            sa.Column("provider", sa.String(32), server_default="local"),
            sa.Column("content_type", sa.String(128), server_default="application/octet-stream"),
            sa.Column("size_bytes", sa.Integer(), server_default="0"),
            sa.Column("checksum_sha256", sa.String(64), server_default=""),
            sa.Column("version_id", sa.String(128), server_default=""),
            sa.Column("original_name", sa.String(255), server_default=""),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("legal_hold", sa.Integer(), server_default="0"),
            sa.Column("row_version", sa.Integer(), server_default="1"),
            sa.Column("create_time", sa.DateTime()),
            sa.Column("update_time", sa.DateTime()),
        )
        op.create_index("ix_object_files_workspace_id", "object_files", ["workspace_id"])
        op.create_index("ix_object_files_storage_key", "object_files", ["storage_key"])
        op.create_index("ix_object_files_deleted_at", "object_files", ["deleted_at"])

    # PostgreSQL: partitioned parents for high-volume time series (dual-write ready)
    if _dialect() == "postgresql":
        op.execute(
            """
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
            """
        )
        op.execute(
            """
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
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_sal_p_ws_created ON security_audit_logs_p (workspace_id, created_at)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_wr_p_ws_time ON workflow_runs_p (workspace_id, create_time)"
        )


def downgrade() -> None:
    if _dialect() == "postgresql":
        op.execute("DROP TABLE IF EXISTS workflow_runs_p CASCADE")
        op.execute("DROP TABLE IF EXISTS security_audit_logs_p CASCADE")

    insp = sa.inspect(op.get_bind())
    if "object_files" in insp.get_table_names():
        op.drop_table("object_files")

    # Do not drop additive columns on live resource tables in downgrade —
    # expand/contract: leaving nullable columns is safer for zero-downtime rollback.
