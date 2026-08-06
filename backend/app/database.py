import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # argon2id (legacy md5 migrated on login)
    email = Column(String(255), nullable=True, index=True)
    oauth_provider = Column(String(32), nullable=True)
    oauth_subject = Column(String(128), nullable=True, index=True)
    role = Column(String(32), default="admin")  # Default to admin for all users
    email_verified = Column(Integer, default=0)
    mfa_enabled = Column(Integer, default=0)
    mfa_secret_enc = Column(Text, default="")
    password_changed_at = Column(DateTime, nullable=True)
    must_change_password = Column(Integer, default=0)  # 1 = force password change before API use
    delete = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User-specific API configuration
    user_api_key_enc = Column(Text, nullable=True)  # Encrypted user's personal API key
    user_api_provider = Column(String(32), nullable=True, default="openrouter")  # Provider type
    user_api_model = Column(String(120), nullable=True, default="openai/gpt-4o-mini")  # User's preferred model
    user_api_base_url = Column(String(512), nullable=True, default="")  # Custom base URL if needed


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    fingerprint = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    ip_address = Column(String(64), default="")
    device_name = Column(String(120), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    absolute_expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(64), default="")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    session_id = Column(String(32), ForeignKey("auth_sessions.id"), nullable=False, index=True)
    family_id = Column(String(32), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(64), default="")
    replaced_by = Column(String(64), default="")


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetCode(Base):
    """One-time, short-lived password reset verification codes."""

    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    attempts = Column(Integer, default=0)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(120), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    workspace_id = Column(Integer, nullable=True, index=True)
    resource_type = Column(String(64), default="")
    resource_id = Column(String(128), default="")
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    success = Column(Integer, default=1)
    detail_json = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(80), nullable=False)
    desc = Column(String(500), default="")
    prompt = Column(Text, nullable=False)
    logo = Column(String(255), default="")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    status = Column(Integer, default=0)  # 0 offline, 1 online
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), default="")
    model = Column(String(120), default="text-embedding-3-small")
    type = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("KnowledgeFile", back_populates="knowledge")


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    status = Column(Integer, default=5)  # 5 queued, 1 processing, 2 ready, 3 failed
    error_message = Column(Text, default="")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge = relationship("KnowledgeBase", back_populates="files")
    chunks = relationship("KnowledgeChunk", back_populates="file", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding_json = Column(Text, default="")

    file = relationship("KnowledgeFile", back_populates="chunks")


class KnowledgeFolder(Base):
    """KOS folder — nested hierarchy within a collection (knowledge base)."""

    __tablename__ = "knowledge_folders"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    parent_folder_id = Column(String(32), ForeignKey("knowledge_folders.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    path = Column(String(500), default="")
    labels_json = Column(Text, default="[]")
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeDocumentVersion(Base):
    """KOS document version history."""

    __tablename__ = "knowledge_document_versions"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False, default=1)
    content_hash = Column(String(64), default="")
    file_path = Column(String(500), default="")
    change_summary = Column(Text, default="")
    approval_status = Column(String(16), default="approved")
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class KnowledgeEntity(Base):
    """KOS knowledge graph entity."""

    __tablename__ = "knowledge_entities"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True, index=True)
    file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=True, index=True)
    entity_type = Column(String(32), default="concept", index=True)
    name = Column(String(200), nullable=False, index=True)
    aliases_json = Column(Text, default="[]")
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)


class KnowledgeRelationship(Base):
    """KOS knowledge graph relationship."""

    __tablename__ = "knowledge_relationships"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    source_entity_id = Column(String(32), ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    target_entity_id = Column(String(32), ForeignKey("knowledge_entities.id"), nullable=False, index=True)
    relation_type = Column(String(64), default="related_to", index=True)
    confidence = Column(Float, default=1.0)
    source_file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=True)
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)


class KnowledgeTag(Base):
    """KOS tag/label on collections or documents."""

    __tablename__ = "knowledge_tags"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True, index=True)
    file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=True, index=True)
    label = Column(String(64), nullable=False, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class KnowledgeSyncJob(Base):
    """KOS ingestion sync job (S3, Git, webhook, etc.)."""

    __tablename__ = "knowledge_sync_jobs"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    connector_type = Column(String(32), default="manual", index=True)
    status = Column(String(16), default="pending", index=True)
    config_json = Column(Text, default="{}")
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    error_message = Column(Text, default="")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssistantKnowledge(Base):
    __tablename__ = "assistant_knowledge"

    assistant_id = Column(String(32), ForeignKey("assistants.id"), primary_key=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_bases.id"), primary_key=True)


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(80), nullable=False)
    desc = Column(String(500), default="")
    graph_json = Column(Text, default="{}")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    status = Column(Integer, default=0)  # 0 draft, 1 published
    webhook_token = Column(String(64), default="")
    is_public = Column(Integer, default=0)  # marketplace listing
    run_webhook_url = Column(String(500), default="")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowPresence(Base):
    __tablename__ = "workflow_presence"

    workflow_id = Column(String(32), ForeignKey("workflows.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user_name = Column(String(80), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowPresenceSession(Base):
    __tablename__ = "workflow_presence_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    user_name = Column(String(80), default="")
    cursor_x = Column(Float, default=0)
    cursor_y = Column(Float, default=0)
    selected_id = Column(String(64), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowPendingRun(Base):
    __tablename__ = "workflow_pending_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    context_json = Column(Text, default="{}")
    graph_json = Column(Text, default="{}")
    pause_after_node = Column(String(64), default="")
    steps_json = Column(Text, default="[]")
    status = Column(Integer, default=0)  # 0 pending, 1 resumed, 2 rejected
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    name = Column(String(80), default="")
    desc = Column(String(500), default="")
    graph_json = Column(Text, default="{}")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowRating(Base):
    __tablename__ = "workflow_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    score = Column(Integer, nullable=False)
    comment = Column(String(500), default="")
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowComment(Base):
    __tablename__ = "workflow_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user_name = Column(String(80), default="")
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    body = Column(String(1000), nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowSchedule(Base):
    __tablename__ = "workflow_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    cron_expression = Column(String(64), nullable=False)
    input_text = Column(String(2000), default="")
    enabled = Column(Integer, default=1)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False)
    key_prefix = Column(String(16), default="")
    key_hash = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    input_text = Column(Text, default="")
    output_text = Column(Text, default="")
    steps_json = Column(Text, default="[]")
    status = Column(Integer, default=1)
    duration_ms = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False)
    resource_id = Column(String(64), default="")
    meta = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkspaceSetting(Base):
    __tablename__ = "workspace_settings"

    id = Column(Integer, primary_key=True, default=1)
    chat_model = Column(String(120), default="")
    embedding_model = Column(String(120), default="")
    openai_base_url = Column(String(255), default="")
    active_provider_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LlmProvider(Base):
    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    provider_type = Column(String(32), nullable=False, default="openai")
    base_url = Column(String(512), default="")
    api_key_enc = Column(Text, default="")
    chat_model = Column(String(120), default="")
    embedding_model = Column(String(120), default="")
    is_active = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeamInvitation(Base):
    __tablename__ = "team_invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    invited_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    invited_email = Column(String(255), nullable=False, index=True)
    invited_role = Column(String(32), default="editor")  # Role to assign when accepted
    invitation_token = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(32), default="pending")  # pending, accepted, rejected, expired
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvalSuite(Base):
    __tablename__ = "eval_suites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), default="")
    assistant_id = Column(String(32), ForeignKey("assistants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cases = relationship(
        "EvalCase",
        back_populates="suite",
        cascade="all, delete-orphan",
        order_by="EvalCase.sort_order",
    )
    runs = relationship("EvalRun", back_populates="suite", cascade="all, delete-orphan")


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=False)
    input_text = Column(Text, nullable=False)
    expected_text = Column(Text, default="")
    match_type = Column(String(16), default="contains")  # contains | exact
    sort_order = Column(Integer, default=0)

    suite = relationship("EvalSuite", back_populates="cases")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    status = Column(String(16), default="completed")
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, default=0)
    results_json = Column(Text, default="[]")
    create_time = Column(DateTime, default=datetime.utcnow)

    suite = relationship("EvalSuite", back_populates="runs")


class EvalSchedule(Base):
    __tablename__ = "eval_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    interval_hours = Column(Integer, default=24)
    cron_expression = Column(String(64), default="")
    enabled = Column(Integer, default=1)
    scoring = Column(String(16), default="rules")
    judge_threshold = Column(Integer, default=4)
    webhook_url = Column(String(500), default="")
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    suite = relationship("EvalSuite")


class EvalRegressionAlert(Base):
    __tablename__ = "eval_regression_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    min_pass_rate = Column(Integer, default=80)
    drop_points = Column(Integer, default=10)
    webhook_url = Column(String(500), default="")
    pagerduty_routing_key = Column(String(64), default="")
    opsgenie_api_key = Column(String(128), default="")
    email_to = Column(String(255), default="")
    use_workspace_slack = Column(Integer, default=0)
    cooldown_hours = Column(Integer, default=6)
    enabled = Column(Integer, default=1)
    last_alert_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    suite = relationship("EvalSuite")


class EvalComparison(Base):
    __tablename__ = "eval_comparisons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    assistant_ids_json = Column(Text, default="[]")
    scoring = Column(String(16), default="rules")
    results_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)

    suite = relationship("EvalSuite")


class FineTuneDataset(Base):
    __tablename__ = "finetune_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500), default="")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    rows_json = Column(Text, default="[]")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("FineTuneJob", back_populates="dataset", cascade="all, delete-orphan")


class FineTuneJob(Base):
    __tablename__ = "finetune_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("finetune_datasets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True)
    base_model = Column(String(120), default="gpt-4o-mini-2024-07-18")
    status = Column(String(24), default="pending")
    openai_file_id = Column(String(64), default="")
    job_id = Column(String(64), default="")
    fine_tuned_model = Column(String(120), default="")
    error_message = Column(Text, default="")
    webhook_url = Column(String(500), default="")
    webhook_sent = Column(Integer, default=0)
    auto_eval_suite_id = Column(Integer, ForeignKey("eval_suites.id"), nullable=True)
    auto_eval_run_id = Column(Integer, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("FineTuneDataset", back_populates="jobs")


class DevProject(Base):
    __tablename__ = "dev_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    status = Column(String(24), default="active")
    integrations_json = Column(Text, default="{}")
    workflow_ids_json = Column(Text, default="[]")
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceIntegration(Base):
    __tablename__ = "workspace_integrations"

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), primary_key=True)
    telegram_bot_token_enc = Column(Text, default="")
    telegram_bot_username = Column(String(64), default="")
    telegram_default_chat_id = Column(String(32), default="")
    smtp_host = Column(String(255), default="")
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255), default="")
    smtp_password_enc = Column(Text, default="")
    smtp_from = Column(String(255), default="")
    gmail_preset = Column(Integer, default=0)
    # smtp | oauth
    gmail_auth_mode = Column(String(16), default="smtp")
    gmail_oauth_refresh_token_enc = Column(Text, default="")
    gmail_oauth_access_token_enc = Column(Text, default="")
    gmail_oauth_token_expiry = Column(DateTime, nullable=True)
    gmail_oauth_email = Column(String(255), default="")
    gmail_oauth_connected_at = Column(DateTime, nullable=True)
    # Jira Cloud
    jira_base_url = Column(String(500), default="")
    jira_email = Column(String(255), default="")
    jira_api_token_enc = Column(Text, default="")
    # Slack incoming webhook (optional default channel webhook)
    slack_webhook_url_enc = Column(Text, default="")
    slack_default_channel = Column(String(120), default="")
    # Slack Bot / Events API (inbound)
    slack_bot_token_enc = Column(Text, default="")
    slack_signing_secret_enc = Column(Text, default="")
    slack_events_workflow_id = Column(String(32), default="")
    slack_events_url = Column(String(500), default="")
    slack_events_registered_at = Column(DateTime, nullable=True)
    # Discord incoming webhook
    discord_webhook_url_enc = Column(Text, default="")
    discord_default_channel = Column(String(120), default="")
    # GitHub Issues (PAT)
    github_token_enc = Column(Text, default="")
    github_owner = Column(String(120), default="")
    github_repo = Column(String(120), default="")
    # Linear Issues
    linear_api_key_enc = Column(Text, default="")
    linear_team_id = Column(String(64), default="")
    public_base_url = Column(String(500), default="")
    telegram_webhook_workflow_id = Column(String(32), default="")
    telegram_webhook_url = Column(String(500), default="")
    telegram_webhook_registered_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class CredentialVaultEntry(Base):
    """Named multi-slot credentials vault (multiple Gmails, LLMs, bots, etc.)."""

    __tablename__ = "credential_vault"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    category = Column(String(32), nullable=False, index=True)  # llm, email, telegram, ...
    kind = Column(String(64), nullable=False, default="custom", index=True)  # openai, gmail_smtp, ...
    label = Column(String(120), nullable=False, default="default")
    fields_enc = Column(Text, default="")  # Fernet JSON blob of secret+nonsecret fields
    public_meta_json = Column(Text, default="{}")  # non-secret display fields (masked hints)
    is_default = Column(Integer, default=0, index=True)
    status = Column(String(24), default="unverified")  # unverified|ok|error
    last_verified_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SavedAgent(Base):
    __tablename__ = "saved_agents"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(80), nullable=False)
    desc = Column(String(500), default="")
    system_prompt = Column(Text, default="")
    tools_json = Column(Text, default="[]")
    knowledge_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    status = Column(Integer, default=1)  # 1 active
    agent_type = Column(String(32), default="custom")
    lifecycle_status = Column(String(16), default="published")
    version_no = Column(Integer, default=1)
    capabilities_json = Column(Text, default="[]")
    policies_json = Column(Text, default="{}")
    template_id = Column(String(32), default="")
    metadata_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentRun(Base):
    """AgentOS execution session — long-running task tracking."""

    __tablename__ = "agent_runs"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String(32), ForeignKey("saved_agents.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    conversation_id = Column(String(32), nullable=True, index=True)
    supervisor_id = Column(String(32), nullable=True, index=True)
    mode = Column(String(32), default="single", index=True)
    status = Column(String(16), default="running", index=True)
    input_text = Column(Text, default="")
    output_text = Column(Text, default="")
    plan_json = Column(Text, default="{}")
    reasoning_json = Column(Text, default="{}")
    verification_json = Column(Text, default="{}")
    metrics_json = Column(Text, default="{}")
    trace_id = Column(String(64), default="", index=True)
    confidence = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    error_message = Column(Text, default="")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AgentCheckpoint(Base):
    """AgentOS checkpoint for pause/resume/recovery."""

    __tablename__ = "agent_checkpoints"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    run_id = Column(String(32), ForeignKey("agent_runs.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    step_no = Column(Integer, default=0)
    state_json = Column(Text, default="{}")
    status = Column(String(16), default="saved")
    create_time = Column(DateTime, default=datetime.utcnow)


class AgentPlanSession(Base):
    """AgentOS planning session with dependency graph."""

    __tablename__ = "agent_plan_sessions"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    run_id = Column(String(32), ForeignKey("agent_runs.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    goal = Column(Text, default="")
    plan_json = Column(Text, default="{}")
    dependencies_json = Column(Text, default="[]")
    status = Column(String(16), default="active")
    create_time = Column(DateTime, default=datetime.utcnow)


class AgentVerificationReport(Base):
    """AgentOS verification report."""

    __tablename__ = "agent_verification_reports"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    run_id = Column(String(32), ForeignKey("agent_runs.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    verdict = Column(String(16), default="pending")
    confidence = Column(Float, default=0.0)
    sources_json = Column(Text, default="[]")
    report_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)


class AgentLearningRecord(Base):
    """AgentOS learning analytics — no model retraining."""

    __tablename__ = "agent_learning_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(32), ForeignKey("agent_runs.id"), nullable=True, index=True)
    agent_id = Column(String(32), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    success = Column(Integer, default=1)
    retry_count = Column(Integer, default=0)
    tool_quality = Column(Float, default=0.0)
    knowledge_quality = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class ConnectorConnection(Base):
    """ECP connector connection — named instance per workspace."""

    __tablename__ = "connector_connections"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    connector_type = Column(String(64), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    auth_type = Column(String(32), default="api_key")
    status = Column(String(16), default="active", index=True)
    lifecycle_status = Column(String(16), default="published")
    capabilities_json = Column(Text, default="[]")
    config_json = Column(Text, default="{}")
    health_status = Column(String(16), default="unknown")
    last_health_at = Column(DateTime, nullable=True)
    version_no = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    trace_id = Column(String(64), default="")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConnectorCredential(Base):
    """ECP encrypted credential store with versioning."""

    __tablename__ = "connector_credentials"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    connection_id = Column(String(32), ForeignKey("connector_connections.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    credential_type = Column(String(32), default="secret")
    secret_enc = Column(Text, default="")
    version_no = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=True)
    rotated_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ConnectorSyncJob(Base):
    """ECP sync job — incremental/scheduled/webhook sync."""

    __tablename__ = "connector_sync_jobs"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    connection_id = Column(String(32), ForeignKey("connector_connections.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    direction = Column(String(16), default="inbound")
    mode = Column(String(16), default="incremental")
    status = Column(String(16), default="pending", index=True)
    checkpoint_json = Column(Text, default="{}")
    config_json = Column(Text, default="{}")
    error_message = Column(Text, default="")
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConnectorWebhook(Base):
    """ECP webhook subscription — inbound/outbound."""

    __tablename__ = "connector_webhooks"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    connection_id = Column(String(32), ForeignKey("connector_connections.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    direction = Column(String(16), default="inbound")
    url = Column(String(500), default="")
    secret_enc = Column(Text, default="")
    events_json = Column(Text, default="[]")
    status = Column(String(16), default="active")
    last_delivery_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ConnectorEvent(Base):
    """ECP event log for replay and observability."""

    __tablename__ = "connector_events"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    connection_id = Column(String(32), nullable=True, index=True)
    event_type = Column(String(64), default="connector.action", index=True)
    direction = Column(String(16), default="outbound")
    status = Column(String(16), default="pending", index=True)
    payload_json = Column(Text, default="{}")
    trace_id = Column(String(64), default="", index=True)
    latency_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class MCPRegistration(Base):
    """ECP Model Context Protocol server/client registration."""

    __tablename__ = "mcp_registrations"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    role = Column(String(16), default="client")
    transport = Column(String(16), default="stdio")
    endpoint = Column(String(500), default="")
    capabilities_json = Column(Text, default="[]")
    tools_json = Column(Text, default="[]")
    auth_type = Column(String(32), default="none")
    status = Column(String(16), default="active")
    version = Column(String(16), default="1.0")
    config_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EIAPRecommendation(Base):
    """EIAP recommendation — approval-gated optimization suggestion. Never auto-applied."""

    __tablename__ = "eiap_recommendations"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    domain = Column(String(32), default="workflow", index=True)  # workflow|agent|knowledge|connectivity|model|finops|prompt|search
    category = Column(String(64), default="optimization")
    severity = Column(String(16), default="info")  # info|low|medium|high|critical
    title = Column(String(200), default="")
    detail = Column(Text, default="")
    resource_type = Column(String(64), default="")
    resource_id = Column(String(64), default="")
    evidence_json = Column(Text, default="{}")
    estimated_impact = Column(String(200), default="")
    status = Column(String(16), default="open", index=True)  # open|approved|applied|dismissed
    reviewed_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    trace_id = Column(String(64), default="")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EIAPReport(Base):
    """EIAP generated report — daily/weekly/monthly/executive snapshots."""

    __tablename__ = "eiap_reports"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    report_type = Column(String(32), default="daily", index=True)
    period = Column(String(32), default="")
    payload_json = Column(Text, default="{}")
    summary = Column(Text, default="")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class AIMemoryEntry(Base):
    """Tenant-scoped AI memory (conversation, workspace, project, agent, pinned, semantic)."""

    __tablename__ = "ai_memory_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    scope = Column(String(32), default="workspace", index=True)
    scope_ref = Column(String(128), default="", index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    content = Column(Text, default="")
    meta_json = Column(Text, default="")
    pinned = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowExecutionCheckpoint(Base):
    """Checkpoint for pause/resume/replay workflow execution."""

    __tablename__ = "workflow_execution_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    node_id = Column(String(64), default="")
    context_json = Column(Text, default="{}")
    steps_json = Column(Text, default="[]")
    status = Column(String(32), default="paused")
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkflowTestCase(Base):
    """Saved workflow test case for regression/replay testing."""

    __tablename__ = "workflow_test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(120), default="")
    input_text = Column(Text, default="")
    expected_contains = Column(Text, default="")
    mock_mode = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformMetric(Base):
    """Telemetry sample — HTTP, AI runtime, workflow, workers."""

    __tablename__ = "platform_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subsystem = Column(String(32), nullable=False, index=True)
    operation = Column(String(128), default="", index=True)
    trace_id = Column(String(32), default="", index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    latency_ms = Column(Integer, default=0)
    status = Column(String(16), default="ok")
    provider = Column(String(64), default="")
    model = Column(String(120), default="")
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class PlatformEvent(Base):
    """Domain event stream — filterable, correlatable, auditable."""

    __tablename__ = "platform_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    trace_id = Column(String(32), default="", index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    resource_type = Column(String(64), default="")
    resource_id = Column(String(128), default="")
    payload_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class PlatformPolicy(Base):
    """Centralized policy rules — workspace/org scoped."""

    __tablename__ = "platform_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    policy_type = Column(String(32), nullable=False, index=True)
    scope = Column(String(32), default="workspace")
    rule_key = Column(String(64), nullable=False)
    rule_value = Column(Text, default="")
    severity = Column(String(16), default="enforce")
    enabled = Column(Integer, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformBudget(Base):
    """Workspace FinOps budget."""

    __tablename__ = "platform_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    monthly_limit_usd = Column(Float, default=0.0)
    enabled = Column(Integer, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIOSKernelConfig(Base):
    """NovaFlow AIOS Core Kernel Configuration."""

    __tablename__ = "aios_kernel_config"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    active_provider_id = Column(Integer, nullable=True)
    heartbeat_interval = Column(Integer, default=30)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CapabilityDNA(Base):
    """Stores the capability schema metadata definitions."""

    __tablename__ = "aios_capability_dna"

    id = Column(String(36), primary_key=True)
    category = Column(String(64), nullable=False)
    inputs_json = Column(Text, default="{}")
    outputs_json = Column(Text, default="{}")
    latency_budget_ms = Column(Integer, default=500)
    reliability_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UniversalCapability(Base):
    """Stores active capability registrations across workspace environments."""

    __tablename__ = "aios_universal_capabilities"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    dna_id = Column(String(36), ForeignKey("aios_capability_dna.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    status = Column(String(16), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class UniversalAsset(Base):
    """Catalog index for all workflows, prompts, agent templates."""

    __tablename__ = "aios_universal_assets"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False, index=True) # workflow|prompt|agent_template
    name = Column(String(120), nullable=False)
    config_json = Column(Text, default="{}")
    version = Column(String(32), default="1.0.0")
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowFragment(Base):
    """Reusable sub-graphs of workflow node DAGs."""

    __tablename__ = "aios_workflow_fragments"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    graph_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectGraph(Base):
    """Root mapping object associating operational goals to solution plans."""

    __tablename__ = "aios_project_graphs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    business_goal = Column(Text, nullable=False)
    solution_payload = Column(Text, default="{}")
    status = Column(String(32), default="draft")
    version_tag = Column(String(32), default="1.0.0")
    created_at = Column(DateTime, default=datetime.utcnow)


class SolutionGraph(Base):
    """Renders the compiled connection mappings of workflows, databases, and agents."""

    __tablename__ = "aios_solution_graphs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    project_id = Column(String(36), ForeignKey("aios_project_graphs.id"), nullable=False, index=True)
    graph_payload = Column(Text, default="{}")
    version_tag = Column(String(32), default="1.0.0")
    status = Column(String(32), default="compiled")
    created_at = Column(DateTime, default=datetime.utcnow)


class HierarchicalMemory(Base):
    """Context database partition supporting workspace, solution, and agent scoping."""

    __tablename__ = "aios_hierarchical_memories"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    scope = Column(String(32), default="workspace", index=True) # workspace|solution|agent|user
    scope_ref = Column(String(128), default="", index=True)
    content = Column(Text, default="")
    ttl_seconds = Column(Integer, default=2592000) # 30 days
    created_at = Column(DateTime, default=datetime.utcnow)


class CostLedger(Base):
    """FinOps cost ledger — LLM, embedding, storage, workflow."""

    __tablename__ = "cost_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    cost_type = Column(String(32), nullable=False, index=True)
    amount_usd = Column(Float, default=0.0)
    trace_id = Column(String(32), default="")
    model = Column(String(120), default="")
    resource_type = Column(String(64), default="")
    resource_id = Column(String(128), default="")
    meta_json = Column(Text, default="{}")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(String(200), default="")
    message = Column(Text, default="")
    category = Column(String(32), default="INFO", index=True)
    level = Column(String(16), default="INFO", index=True)
    is_read = Column(Integer, default=0, index=True)
    action_url = Column(String(500), default="")
    create_time = Column(DateTime, default=datetime.utcnow, index=True)


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, unique=True, index=True)
    enabled_categories = Column(Text, default="[]")  # JSON list
    enabled_channels = Column(Text, default="[]")    # JSON list
    muted_categories = Column(Text, default="[]")    # JSON list
    do_not_disturb = Column(Integer, default=0)
    quiet_hours_start = Column(String(5), default="22:00")
    quiet_hours_end = Column(String(5), default="08:00")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Enterprise conversation — permanent record for all AI interactions."""

    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(String(200), default="New conversation")
    summary = Column(Text, default="")
    tags_json = Column(Text, default="[]")
    conversation_type = Column(String(32), default="assistant", index=True)
    resource_id = Column(String(64), default="", index=True)
    visibility = Column(String(16), default="private")
    status = Column(String(16), default="active", index=True)
    pinned = Column(Integer, default=0)
    starred = Column(Integer, default=0)
    parent_branch_id = Column(String(32), nullable=True)
    meta_json = Column(Text, default="{}")
    legal_hold = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow, index=True)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    parent_thread_id = Column(String(32), nullable=True, index=True)
    title = Column(String(200), default="")
    pinned = Column(Integer, default=0)
    archived = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    thread_id = Column(String(32), ForeignKey("conversation_threads.id"), nullable=True, index=True)
    parent_message_id = Column(String(32), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    message_type = Column(String(16), default="user", index=True)
    role = Column(String(16), default="user")
    content = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    assistant_id = Column(String(32), default="")
    model = Column(String(120), default="")
    provider = Column(String(64), default="")
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    trace_id = Column(String(32), default="", index=True)
    visibility = Column(String(16), default="private")
    knowledge_refs_json = Column(Text, default="[]")
    tool_calls_json = Column(Text, default="[]")
    citations_json = Column(Text, default="[]")
    workflow_ref = Column(String(64), default="")
    agent_ref = Column(String(64), default="")
    attachment_ids_json = Column(Text, default="[]")
    meta_json = Column(Text, default="{}")
    version = Column(Integer, default=1)
    deleted_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow, index=True)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationBranch(Base):
    __tablename__ = "conversation_branches"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    parent_message_id = Column(String(32), nullable=True)
    branch_conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False)
    status = Column(String(16), default="active")
    merged_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ConversationAttachment(Base):
    __tablename__ = "conversation_attachments"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    message_id = Column(String(32), ForeignKey("conversation_messages.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    file_name = Column(String(255), default="")
    mime_type = Column(String(128), default="")
    size_bytes = Column(Integer, default=0)
    storage_key = Column(String(512), default="")
    extracted_text = Column(Text, default="")
    extract_status = Column(String(16), default="pending")  # pending|ready|failed|skipped
    knowledge_id = Column(Integer, nullable=True)
    knowledge_file_id = Column(Integer, nullable=True)
    meta_json = Column(Text, default="{}")
    version = Column(Integer, default=1)
    deleted_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ConversationShare(Base):
    __tablename__ = "conversation_shares"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    share_token = Column(String(64), unique=True, index=True)
    permission = Column(String(16), default="read")
    expires_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ConversationSnapshot(Base):
    __tablename__ = "conversation_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False, index=True)
    version_no = Column(Integer, default=1)
    snapshot_json = Column(Text, default="{}")
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class Organization(Base):
    """Top-level tenant container (company / university / government)."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(160), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    logo_url = Column(String(500), default="")
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    plan = Column(String(32), default="free")  # free | team | business | enterprise
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id = Column(Integer, ForeignKey("organizations.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    role = Column(String(32), default="member")  # owner | admin | member | billing
    create_time = Column(DateTime, default=datetime.utcnow)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    workspace_type = Column(String(32), default="personal")  # personal | team | organization | enterprise
    logo_url = Column(String(500), default="")
    region = Column(String(64), default="global")
    timezone = Column(String(64), default="UTC")
    language = Column(String(16), default="en")
    visibility = Column(String(16), default="private")
    deleted_at = Column(DateTime, nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceQuota(Base):
    __tablename__ = "workspace_quotas"

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), primary_key=True)
    eval_runs_monthly_limit = Column(Integer, default=0)
    finetune_jobs_monthly_limit = Column(Integer, default=0)
    seat_limit = Column(Integer, default=0)  # 0 = unlimited
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AbModelRoute(Base):
    __tablename__ = "ab_model_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True)
    base_model = Column(String(120), default="")
    variant_model = Column(String(120), default="")
    variant_traffic_pct = Column(Integer, default=50)
    enabled = Column(Integer, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    parent_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), nullable=False, index=True)
    description = Column(String(500), default="")
    leader_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(Integer, ForeignKey("teams.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    role = Column(String(32), default="member")  # lead | member
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    role = Column(String(32), default="editor")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(32), default="editor")
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(16), default="pending")  # pending | accepted | rejected | expired | revoked
    invited_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    accepted_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class EmergencyAccessGrant(Base):
    """Break-glass platform access to customer workspaces — always audited."""

    __tablename__ = "emergency_access_grants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    grantee_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    reason = Column(String(500), nullable=False)
    status = Column(String(16), default="pending")  # pending | active | revoked | expired | denied
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)


class ObjectFile(Base):
    """Object storage metadata — bytes live in R2/S3/MinIO/local, not in PostgreSQL."""

    __tablename__ = "object_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    team_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    visibility = Column(String(16), default="workspace")
    tenant_version = Column(Integer, default=1)
    storage_key = Column(String(512), nullable=False, index=True)
    bucket = Column(String(128), default="")
    provider = Column(String(32), default="local")
    content_type = Column(String(128), default="application/octet-stream")
    size_bytes = Column(Integer, default=0)
    checksum_sha256 = Column(String(64), default="")
    version_id = Column(String(128), default="")
    original_name = Column(String(255), default="")
    deleted_at = Column(DateTime, nullable=True, index=True)
    legal_hold = Column(Integer, default=0)
    row_version = Column(Integer, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


try:
    from app.data.engine import create_data_engine
    from app.data.observability import attach_engine_metrics

    engine = create_data_engine(DATABASE_URL)
    attach_engine_metrics(engine)
except Exception:
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def migrate_schema():
    """Lightweight SQLite/MySQL column migrations for dev upgrades."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "knowledge_chunks" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_chunks")}
        if "embedding_json" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE knowledge_chunks ADD COLUMN embedding_json TEXT"))
    if "knowledge_files" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_files")}
        if "error_message" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE knowledge_files ADD COLUMN error_message TEXT"))
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "role" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'editor'"))
                conn.execute(text("UPDATE users SET role = 'admin' WHERE user_id = 1"))
        for col, ddl in [
            ("email", "ALTER TABLE users ADD COLUMN email VARCHAR(255)"),
            ("oauth_provider", "ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(32)"),
            ("oauth_subject", "ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(128)"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    workspace_cols = {
        "assistants": "ALTER TABLE assistants ADD COLUMN workspace_id INTEGER",
        "knowledge_bases": "ALTER TABLE knowledge_bases ADD COLUMN workspace_id INTEGER",
        "workflows": "ALTER TABLE workflows ADD COLUMN workspace_id INTEGER",
        "workflow_runs": "ALTER TABLE workflow_runs ADD COLUMN workspace_id INTEGER",
        "usage_events": "ALTER TABLE usage_events ADD COLUMN workspace_id INTEGER",
    }
    for table, ddl in workspace_cols.items():
        if table in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns(table)}
            if "workspace_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "finetune_jobs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("finetune_jobs")}
        for col, ddl in [
            ("webhook_url", "ALTER TABLE finetune_jobs ADD COLUMN webhook_url VARCHAR(500) DEFAULT ''"),
            ("webhook_sent", "ALTER TABLE finetune_jobs ADD COLUMN webhook_sent INTEGER DEFAULT 0"),
            ("auto_eval_suite_id", "ALTER TABLE finetune_jobs ADD COLUMN auto_eval_suite_id INTEGER"),
            ("auto_eval_run_id", "ALTER TABLE finetune_jobs ADD COLUMN auto_eval_run_id INTEGER"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "dev_projects" not in insp.get_table_names():
        Base.metadata.tables["dev_projects"].create(bind=engine, checkfirst=True)

    if "workspace_integrations" not in insp.get_table_names():
        Base.metadata.tables["workspace_integrations"].create(bind=engine, checkfirst=True)
    elif "workspace_integrations" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workspace_integrations")}
        for col, ddl in [
            ("public_base_url", "ALTER TABLE workspace_integrations ADD COLUMN public_base_url VARCHAR(500) DEFAULT ''"),
            ("telegram_webhook_workflow_id", "ALTER TABLE workspace_integrations ADD COLUMN telegram_webhook_workflow_id VARCHAR(32) DEFAULT ''"),
            ("telegram_webhook_url", "ALTER TABLE workspace_integrations ADD COLUMN telegram_webhook_url VARCHAR(500) DEFAULT ''"),
            ("telegram_webhook_registered_at", "ALTER TABLE workspace_integrations ADD COLUMN telegram_webhook_registered_at DATETIME"),
            ("gmail_auth_mode", "ALTER TABLE workspace_integrations ADD COLUMN gmail_auth_mode VARCHAR(16) DEFAULT 'smtp'"),
            ("gmail_oauth_refresh_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_refresh_token_enc TEXT"),
            ("gmail_oauth_access_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_access_token_enc TEXT"),
            ("gmail_oauth_token_expiry", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_token_expiry DATETIME"),
            ("gmail_oauth_email", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_email VARCHAR(255) DEFAULT ''"),
            ("gmail_oauth_connected_at", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_connected_at DATETIME"),
            ("jira_base_url", "ALTER TABLE workspace_integrations ADD COLUMN jira_base_url VARCHAR(500) DEFAULT ''"),
            ("jira_email", "ALTER TABLE workspace_integrations ADD COLUMN jira_email VARCHAR(255) DEFAULT ''"),
            ("jira_api_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN jira_api_token_enc TEXT"),
            ("slack_webhook_url_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_webhook_url_enc TEXT"),
            ("slack_default_channel", "ALTER TABLE workspace_integrations ADD COLUMN slack_default_channel VARCHAR(120) DEFAULT ''"),
            ("github_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN github_token_enc TEXT"),
            ("github_owner", "ALTER TABLE workspace_integrations ADD COLUMN github_owner VARCHAR(120) DEFAULT ''"),
            ("github_repo", "ALTER TABLE workspace_integrations ADD COLUMN github_repo VARCHAR(120) DEFAULT ''"),
            ("discord_webhook_url_enc", "ALTER TABLE workspace_integrations ADD COLUMN discord_webhook_url_enc TEXT"),
            ("discord_default_channel", "ALTER TABLE workspace_integrations ADD COLUMN discord_default_channel VARCHAR(120) DEFAULT ''"),
            ("linear_api_key_enc", "ALTER TABLE workspace_integrations ADD COLUMN linear_api_key_enc TEXT"),
            ("linear_team_id", "ALTER TABLE workspace_integrations ADD COLUMN linear_team_id VARCHAR(64) DEFAULT ''"),
            ("slack_bot_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_bot_token_enc TEXT"),
            ("slack_signing_secret_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_signing_secret_enc TEXT"),
            ("slack_events_workflow_id", "ALTER TABLE workspace_integrations ADD COLUMN slack_events_workflow_id VARCHAR(32) DEFAULT ''"),
            ("slack_events_url", "ALTER TABLE workspace_integrations ADD COLUMN slack_events_url VARCHAR(500) DEFAULT ''"),
            ("slack_events_registered_at", "ALTER TABLE workspace_integrations ADD COLUMN slack_events_registered_at DATETIME"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "saved_agents" not in insp.get_table_names():
        Base.metadata.tables["saved_agents"].create(bind=engine, checkfirst=True)

    if "eval_schedules" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("eval_schedules")}
        if "cron_expression" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE eval_schedules ADD COLUMN cron_expression VARCHAR(64) DEFAULT ''"))

    if "eval_regression_alerts" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("eval_regression_alerts")}
        for col, ddl in [
            ("pagerduty_routing_key", "ALTER TABLE eval_regression_alerts ADD COLUMN pagerduty_routing_key VARCHAR(64) DEFAULT ''"),
            ("opsgenie_api_key", "ALTER TABLE eval_regression_alerts ADD COLUMN opsgenie_api_key VARCHAR(128) DEFAULT ''"),
            ("use_workspace_slack", "ALTER TABLE eval_regression_alerts ADD COLUMN use_workspace_slack INTEGER DEFAULT 0"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "workflows" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workflows")}
        for col, ddl in [
            ("webhook_token", "ALTER TABLE workflows ADD COLUMN webhook_token VARCHAR(64) DEFAULT ''"),
            ("is_public", "ALTER TABLE workflows ADD COLUMN is_public INTEGER DEFAULT 0"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    for table in ("workflow_versions", "workflow_ratings", "workflow_comments", "workflow_schedules", "workflow_presence", "workflow_presence_sessions"):
        if table not in insp.get_table_names():
            Base.metadata.tables[table].create(bind=engine, checkfirst=True)

    if "workflows" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workflows")}
        if "run_webhook_url" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE workflows ADD COLUMN run_webhook_url VARCHAR(500) DEFAULT ''"))

    # Enterprise security + multi-tenant platform tables
    for table in (
        "auth_sessions",
        "refresh_tokens",
        "password_history",
        "password_reset_codes",
        "security_audit_logs",
        "organizations",
        "organization_members",
        "teams",
        "team_members",
        "workspace_invites",
        "emergency_access_grants",
    ):
        if table not in insp.get_table_names() and table in Base.metadata.tables:
            Base.metadata.tables[table].create(bind=engine, checkfirst=True)

    if "workspaces" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workspaces")}
        for col, ddl in [
            ("organization_id", "ALTER TABLE workspaces ADD COLUMN organization_id INTEGER"),
            ("workspace_type", "ALTER TABLE workspaces ADD COLUMN workspace_type VARCHAR(32) DEFAULT 'personal'"),
            ("logo_url", "ALTER TABLE workspaces ADD COLUMN logo_url VARCHAR(500) DEFAULT ''"),
            ("region", "ALTER TABLE workspaces ADD COLUMN region VARCHAR(64) DEFAULT 'global'"),
            ("timezone", "ALTER TABLE workspaces ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC'"),
            ("language", "ALTER TABLE workspaces ADD COLUMN language VARCHAR(16) DEFAULT 'en'"),
            ("visibility", "ALTER TABLE workspaces ADD COLUMN visibility VARCHAR(16) DEFAULT 'private'"),
            ("deleted_at", "ALTER TABLE workspaces ADD COLUMN deleted_at DATETIME"),
            ("created_by", "ALTER TABLE workspaces ADD COLUMN created_by INTEGER"),
            ("updated_by", "ALTER TABLE workspaces ADD COLUMN updated_by INTEGER"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "workspace_members" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workspace_members")}
        if "team_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE workspace_members ADD COLUMN team_id INTEGER"))

    if "workspace_quotas" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("workspace_quotas")}
        if "seat_limit" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE workspace_quotas ADD COLUMN seat_limit INTEGER DEFAULT 0"))

    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        for col, ddl in [
            ("email_verified", "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0"),
            ("mfa_enabled", "ALTER TABLE users ADD COLUMN mfa_enabled INTEGER DEFAULT 0"),
            ("mfa_secret_enc", "ALTER TABLE users ADD COLUMN mfa_secret_enc TEXT"),
            ("password_changed_at", "ALTER TABLE users ADD COLUMN password_changed_at DATETIME"),
            ("must_change_password", "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0"),
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
        # Widen password column for Argon2id hashes (MySQL); SQLite ignores type width.
        if not DATABASE_URL.startswith("sqlite"):
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NOT NULL"))
            except Exception:
                pass

    # Enterprise data platform — soft delete / optimistic lock / visibility (additive, nullable)
    enterprise_tables = (
        "assistants",
        "knowledge_bases",
        "workflows",
        "workflow_runs",
        "saved_agents",
        "eval_suites",
        "eval_runs",
        "dev_projects",
        "api_keys",
        "fine_tune_datasets",
        "fine_tune_jobs",
    )
    enterprise_cols = {
        "deleted_at": "ALTER TABLE {t} ADD COLUMN deleted_at DATETIME",
        "legal_hold": "ALTER TABLE {t} ADD COLUMN legal_hold INTEGER DEFAULT 0",
        "row_version": "ALTER TABLE {t} ADD COLUMN row_version INTEGER DEFAULT 1",
        "visibility": "ALTER TABLE {t} ADD COLUMN visibility VARCHAR(16) DEFAULT 'workspace'",
        "organization_id": "ALTER TABLE {t} ADD COLUMN organization_id INTEGER",
        "team_id": "ALTER TABLE {t} ADD COLUMN team_id INTEGER",
        "owner_id": "ALTER TABLE {t} ADD COLUMN owner_id INTEGER",
        "created_by": "ALTER TABLE {t} ADD COLUMN created_by INTEGER",
        "updated_by": "ALTER TABLE {t} ADD COLUMN updated_by INTEGER",
        "tenant_version": "ALTER TABLE {t} ADD COLUMN tenant_version INTEGER DEFAULT 1",
    }
    for table in enterprise_tables:
        if table not in insp.get_table_names():
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        for col, ddl_tmpl in enterprise_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl_tmpl.format(t=table)))
                except Exception:
                    pass

    # KOS — extended columns on knowledge tables
    kos_kb_cols = {
        "classification": "ALTER TABLE knowledge_bases ADD COLUMN classification VARCHAR(16) DEFAULT 'internal'",
        "status": "ALTER TABLE knowledge_bases ADD COLUMN status VARCHAR(16) DEFAULT 'published'",
        "tags_json": "ALTER TABLE knowledge_bases ADD COLUMN tags_json TEXT DEFAULT '[]'",
        "labels_json": "ALTER TABLE knowledge_bases ADD COLUMN labels_json TEXT DEFAULT '[]'",
        "aliases_json": "ALTER TABLE knowledge_bases ADD COLUMN aliases_json TEXT DEFAULT '[]'",
        "retention_policy": "ALTER TABLE knowledge_bases ADD COLUMN retention_policy VARCHAR(32) DEFAULT 'standard'",
        "review_required": "ALTER TABLE knowledge_bases ADD COLUMN review_required INTEGER DEFAULT 0",
        "archived_at": "ALTER TABLE knowledge_bases ADD COLUMN archived_at DATETIME",
    }
    if "knowledge_bases" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_bases")}
        for col, ddl in kos_kb_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                except Exception:
                    pass

    kos_file_cols = {
        "folder_id": "ALTER TABLE knowledge_files ADD COLUMN folder_id VARCHAR(32)",
        "version_no": "ALTER TABLE knowledge_files ADD COLUMN version_no INTEGER DEFAULT 1",
        "content_hash": "ALTER TABLE knowledge_files ADD COLUMN content_hash VARCHAR(64) DEFAULT ''",
        "document_type": "ALTER TABLE knowledge_files ADD COLUMN document_type VARCHAR(32) DEFAULT ''",
        "lifecycle_status": "ALTER TABLE knowledge_files ADD COLUMN lifecycle_status VARCHAR(16) DEFAULT 'published'",
        "classification": "ALTER TABLE knowledge_files ADD COLUMN classification VARCHAR(16) DEFAULT 'internal'",
        "metadata_json": "ALTER TABLE knowledge_files ADD COLUMN metadata_json TEXT DEFAULT '{}'",
        "expires_at": "ALTER TABLE knowledge_files ADD COLUMN expires_at DATETIME",
        "owner_id": "ALTER TABLE knowledge_files ADD COLUMN owner_id INTEGER",
    }
    if "knowledge_files" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_files")}
        for col, ddl in kos_file_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                except Exception:
                    pass

    kos_chunk_cols = {
        "content_hash": "ALTER TABLE knowledge_chunks ADD COLUMN content_hash VARCHAR(64) DEFAULT ''",
        "version_no": "ALTER TABLE knowledge_chunks ADD COLUMN version_no INTEGER DEFAULT 1",
    }
    if "knowledge_chunks" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_chunks")}
        for col, ddl in kos_chunk_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                except Exception:
                    pass

    for table_name in (
        "knowledge_folders",
        "knowledge_document_versions",
        "knowledge_entities",
        "knowledge_relationships",
        "knowledge_tags",
        "knowledge_sync_jobs",
        "agent_runs",
        "agent_checkpoints",
        "agent_plan_sessions",
        "agent_verification_reports",
        "agent_learning_records",
        "connector_connections",
        "connector_credentials",
        "connector_sync_jobs",
        "connector_webhooks",
        "connector_events",
        "mcp_registrations",
        "aios_kernel_config",
        "aios_capability_dna",
        "aios_universal_capabilities",
        "aios_universal_assets",
        "aios_workflow_fragments",
        "aios_project_graphs",
        "aios_solution_graphs",
        "aios_hierarchical_memories",
        "eiap_recommendations",
        "eiap_reports",
        "credential_vault",
    ):
        if table_name not in insp.get_table_names() and table_name in Base.metadata.tables:
            try:
                Base.metadata.tables[table_name].create(bind=engine, checkfirst=True)
            except Exception:
                pass

    agent_os_agent_cols = {
        "agent_type": "ALTER TABLE saved_agents ADD COLUMN agent_type VARCHAR(32) DEFAULT 'custom'",
        "lifecycle_status": "ALTER TABLE saved_agents ADD COLUMN lifecycle_status VARCHAR(16) DEFAULT 'published'",
        "version_no": "ALTER TABLE saved_agents ADD COLUMN version_no INTEGER DEFAULT 1",
        "capabilities_json": "ALTER TABLE saved_agents ADD COLUMN capabilities_json TEXT",
        "policies_json": "ALTER TABLE saved_agents ADD COLUMN policies_json TEXT",
        "template_id": "ALTER TABLE saved_agents ADD COLUMN template_id VARCHAR(32) DEFAULT ''",
        "metadata_json": "ALTER TABLE saved_agents ADD COLUMN metadata_json TEXT",
    }
    if "saved_agents" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("saved_agents")}
        for col, ddl in agent_os_agent_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                except Exception:
                    pass

    attachment_cols = {
        "extracted_text": "ALTER TABLE conversation_attachments ADD COLUMN extracted_text TEXT",
        "extract_status": "ALTER TABLE conversation_attachments ADD COLUMN extract_status VARCHAR(16) DEFAULT 'pending'",
        "knowledge_id": "ALTER TABLE conversation_attachments ADD COLUMN knowledge_id INTEGER",
        "knowledge_file_id": "ALTER TABLE conversation_attachments ADD COLUMN knowledge_file_id INTEGER",
        "meta_json": "ALTER TABLE conversation_attachments ADD COLUMN meta_json TEXT",
    }
    if "conversation_attachments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("conversation_attachments")}
        for col, ddl in attachment_cols.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                except Exception:
                    pass


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        from app.services.tenancy import migrate_legacy_workspaces

        migrate_legacy_workspaces(db)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
