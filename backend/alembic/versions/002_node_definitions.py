"""Add workspace node definition library table."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "002_node_definitions"
down_revision = "001_user_role_api_keys"


def upgrade():
    op.create_table(
        "aios_node_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=True, index=True),
        sa.Column("slug", sa.String(80), nullable=False, index=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("definition_json", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft", index=True),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("test_status", sa.String(32), nullable=False, server_default="untested"),
        sa.Column("test_result_json", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=datetime.utcnow),
    )


def downgrade():
    op.drop_table("aios_node_definitions")
