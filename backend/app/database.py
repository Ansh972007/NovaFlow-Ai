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
    status = Column(Integer, default=0)  # 0 draft, 1 published
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(32), ForeignKey("workflows.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
