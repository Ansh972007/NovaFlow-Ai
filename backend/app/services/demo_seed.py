import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.crypto import md5_hash
from app.database import Assistant, AssistantKnowledge, KnowledgeBase, KnowledgeFile, User, Workflow
from app.services.knowledge import kb_upload_dir, process_file_record
from app.services.tenancy import ensure_personal_workspace
from app.services.workflow import DEFAULT_RAG_GRAPH

DEMO_MARKER = DATA_DIR / ".demo_seeded"

SAMPLE_HANDBOOK = """NovaFlow AI — Product Handbook (Demo)

NovaFlow is an enterprise AI workspace for chat, knowledge bases, and visual workflows.

Key features:
- Assistant Studio: configure system prompts and link document libraries for RAG.
- Knowledge bases: upload PDF, TXT, or Markdown files; chunks are embedded for semantic search.
- Workflow builder: drag-and-drop pipelines (trigger → retrieve → LLM → output).
- Team roles: admin, editor, and viewer with read-only enforcement for viewers.
- Analytics: dashboard charts and per-assistant usage on the studio page.

Getting started:
1. Open Chat and select a published assistant.
2. Upload documents under Knowledge, then link them in Assistant Studio.
3. Build a workflow under Workflows and use the Test tab for live step progress.

Support tiers:
- Starter: up to 5 assistants and 2 knowledge bases.
- Team: unlimited assistants, Milvus vector search, team roles.
- Enterprise: SSO, audit logs, dedicated deployment.

Refund policy: 30-day money-back on annual plans. Contact support@novaflow.ai.
SLA: 99.9% uptime on Team and Enterprise plans with 4-hour response for critical issues.
"""


def _already_seeded(db: Session) -> bool:
    if DEMO_MARKER.exists():
        return True
    admin = db.query(User).filter(User.user_name == "admin").first()
    if admin and db.query(Assistant).filter(Assistant.user_id == admin.user_id).count() > 0:
        DEMO_MARKER.parent.mkdir(parents=True, exist_ok=True)
        DEMO_MARKER.touch()
        return True
    return False


def seed_demo_data(db: Session) -> bool:
    """Populate sample assistants, knowledge, and a workflow on a fresh install."""
    if _already_seeded(db):
        return False

    admin = db.query(User).filter(User.user_name == "admin").first()
    if not admin:
        return False

    ws = ensure_personal_workspace(db, admin)
    wid = ws.id

    if not db.query(User).filter(User.user_name == "demo").first():
        demo_user = User(user_name="demo", password=md5_hash("demo123"), role="viewer")
        db.add(demo_user)
        db.flush()
        ensure_personal_workspace(db, demo_user)

    kb = KnowledgeBase(
        name="NovaFlow Handbook",
        description="Sample product docs for RAG demos",
        user_id=admin.user_id,
        workspace_id=wid,
    )
    db.add(kb)
    db.flush()

    dest_dir = kb_upload_dir(kb.id)
    file_name = "novaflow-handbook.txt"
    dest = dest_dir / f"{uuid.uuid4().hex}_{file_name}"
    dest.write_text(SAMPLE_HANDBOOK, encoding="utf-8")
    rel = f"{kb.id}/{dest.name}"
    record = KnowledgeFile(
        knowledge_id=kb.id,
        file_name=file_name,
        file_path=rel,
        status=5,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    process_file_record(db, record, chunk_size=600, chunk_overlap=80)

    support = Assistant(
        name="Support Assistant",
        desc="Answers questions about NovaFlow using the handbook.",
        prompt=(
            "You are NovaFlow customer support. Answer clearly using retrieved context when "
            "available. Be concise and friendly. If unsure, say so and suggest contacting support."
        ),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
    )
    docs = Assistant(
        name="Document Q&A",
        desc="Search and summarize uploaded documents.",
        prompt=(
            "You are a document Q&A assistant. Summarize key points from retrieved chunks "
            "and cite the source document when possible."
        ),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
    )
    db.add(support)
    db.add(docs)
    db.flush()

    db.add(AssistantKnowledge(assistant_id=support.id, knowledge_id=kb.id))
    db.add(AssistantKnowledge(assistant_id=docs.id, knowledge_id=kb.id))

    graph = json.loads(json.dumps(DEFAULT_RAG_GRAPH))
    for node in graph.get("nodes", []):
        if node.get("type") == "retrieve":
            node.setdefault("data", {})["knowledge_id"] = kb.id

    workflow = Workflow(
        name="Handbook Q&A pipeline",
        desc="Retrieve handbook chunks then answer with LLM",
        graph_json=json.dumps(graph),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
    )
    db.add(workflow)
    db.commit()

    DEMO_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DEMO_MARKER.touch()
    print("[NovaFlow] Demo data seeded — assistants, knowledge, and workflow ready.")
    return True
