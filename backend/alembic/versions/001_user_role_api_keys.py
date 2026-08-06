"""Database migration for user role management and per-user API keys."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '001_user_role_api_keys'
down_revision = '0002_enterprise_data_platform'


def upgrade():
    # Add new columns to users table (MySQL compatible)
    op.add_column('users', sa.Column('user_api_key_enc', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('user_api_provider', sa.String(32), nullable=True, server_default='openrouter'))
    op.add_column('users', sa.Column('user_api_model', sa.String(120), nullable=True, server_default='openai/gpt-4o-mini'))
    op.add_column('users', sa.Column('user_api_base_url', sa.String(512), nullable=True, server_default=''))
    
    # Update default role to admin
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'editor'")
    
    # Create team_invitations table
    op.create_table(
        'team_invitations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('invited_by', sa.Integer(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('invited_email', sa.String(255), nullable=False, index=True),
        sa.Column('invited_role', sa.String(32), nullable=False, server_default='editor'),
        sa.Column('invitation_token', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=datetime.utcnow),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=datetime.utcnow, onupdate=datetime.utcnow)
    )


def downgrade():
    # Drop team_invitations table
    op.drop_table('team_invitations')
    
    # Remove new columns from users table
    op.drop_column('users', 'user_api_base_url')
    op.drop_column('users', 'user_api_model')
    op.drop_column('users', 'user_api_provider')
    op.drop_column('users', 'user_api_key_enc')
    
    # Revert default role to editor
    op.execute("UPDATE users SET role = 'editor' WHERE role = 'admin'")