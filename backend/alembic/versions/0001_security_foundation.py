"""Initial enterprise security schema baseline.

Revision ID: 0001_security_foundation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_security_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are also created via Base.metadata.create_all on boot.
    # This revision documents the security foundation for Alembic history.
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if "auth_sessions" not in tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("fingerprint", sa.String(64), server_default=""),
            sa.Column("user_agent", sa.String(512), server_default=""),
            sa.Column("ip_address", sa.String(64), server_default=""),
            sa.Column("device_name", sa.String(120), server_default=""),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("last_seen_at", sa.DateTime()),
            sa.Column("absolute_expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoke_reason", sa.String(64), server_default=""),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("session_id", sa.String(32), sa.ForeignKey("auth_sessions.id"), nullable=False),
            sa.Column("family_id", sa.String(32), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoke_reason", sa.String(64), server_default=""),
            sa.Column("replaced_by", sa.String(64), server_default=""),
        )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("auth_sessions")
