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
    role = Column(String(32), default="editor")
    email_verified = Column(Integer, default=0)
    mfa_enabled = Column(Integer, default=0)
    mfa_secret_enc = Column(Text, default="")
    password_changed_at = Column(DateTime, nullable=True)
    delete = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
                conn.execute(text("ALTER TABLE knowledge_chunks ADD COLUMN embedding_json TEXT DEFAULT ''"))
    if "knowledge_files" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("knowledge_files")}
        if "error_message" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE knowledge_files ADD COLUMN error_message TEXT DEFAULT ''"))
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
            ("gmail_oauth_refresh_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_refresh_token_enc TEXT DEFAULT ''"),
            ("gmail_oauth_access_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_access_token_enc TEXT DEFAULT ''"),
            ("gmail_oauth_token_expiry", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_token_expiry DATETIME"),
            ("gmail_oauth_email", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_email VARCHAR(255) DEFAULT ''"),
            ("gmail_oauth_connected_at", "ALTER TABLE workspace_integrations ADD COLUMN gmail_oauth_connected_at DATETIME"),
            ("jira_base_url", "ALTER TABLE workspace_integrations ADD COLUMN jira_base_url VARCHAR(500) DEFAULT ''"),
            ("jira_email", "ALTER TABLE workspace_integrations ADD COLUMN jira_email VARCHAR(255) DEFAULT ''"),
            ("jira_api_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN jira_api_token_enc TEXT DEFAULT ''"),
            ("slack_webhook_url_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_webhook_url_enc TEXT DEFAULT ''"),
            ("slack_default_channel", "ALTER TABLE workspace_integrations ADD COLUMN slack_default_channel VARCHAR(120) DEFAULT ''"),
            ("github_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN github_token_enc TEXT DEFAULT ''"),
            ("github_owner", "ALTER TABLE workspace_integrations ADD COLUMN github_owner VARCHAR(120) DEFAULT ''"),
            ("github_repo", "ALTER TABLE workspace_integrations ADD COLUMN github_repo VARCHAR(120) DEFAULT ''"),
            ("discord_webhook_url_enc", "ALTER TABLE workspace_integrations ADD COLUMN discord_webhook_url_enc TEXT DEFAULT ''"),
            ("discord_default_channel", "ALTER TABLE workspace_integrations ADD COLUMN discord_default_channel VARCHAR(120) DEFAULT ''"),
            ("linear_api_key_enc", "ALTER TABLE workspace_integrations ADD COLUMN linear_api_key_enc TEXT DEFAULT ''"),
            ("linear_team_id", "ALTER TABLE workspace_integrations ADD COLUMN linear_team_id VARCHAR(64) DEFAULT ''"),
            ("slack_bot_token_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_bot_token_enc TEXT DEFAULT ''"),
            ("slack_signing_secret_enc", "ALTER TABLE workspace_integrations ADD COLUMN slack_signing_secret_enc TEXT DEFAULT ''"),
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
            ("mfa_secret_enc", "ALTER TABLE users ADD COLUMN mfa_secret_enc TEXT DEFAULT ''"),
            ("password_changed_at", "ALTER TABLE users ADD COLUMN password_changed_at DATETIME"),
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
