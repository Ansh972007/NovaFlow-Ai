import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
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
    password = Column(String(128), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    oauth_provider = Column(String(32), nullable=True)
    oauth_subject = Column(String(128), nullable=True, index=True)
    role = Column(String(16), default="editor")  # admin | editor | viewer
    delete = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("FineTuneDataset", back_populates="jobs")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceQuota(Base):
    __tablename__ = "workspace_quotas"

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), primary_key=True)
    eval_runs_monthly_limit = Column(Integer, default=0)
    finetune_jobs_monthly_limit = Column(Integer, default=0)
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


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    role = Column(String(16), default="editor")  # admin | editor | viewer
    create_time = Column(DateTime, default=datetime.utcnow)


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
        ]:
            if col not in cols:
                with engine.begin() as conn:
                    conn.execute(text(ddl))

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

    for table in ("workflow_versions", "workflow_ratings", "workflow_comments", "workflow_schedules"):
        if table not in insp.get_table_names():
            Base.metadata.tables[table].create(bind=engine, checkfirst=True)


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
