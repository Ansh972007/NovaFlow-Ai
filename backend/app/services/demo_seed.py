import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.crypto import hash_password
from app.database import Assistant, AssistantKnowledge, KnowledgeBase, KnowledgeFile, User, Workflow, SavedAgent
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
    lock_dir = DATA_DIR / ".demo_seeded_lock"
    if lock_dir.exists() or DEMO_MARKER.exists():
        return True
    admin = db.query(User).filter(User.user_name == "admin").first()
    if admin and db.query(Assistant).filter(Assistant.user_id == admin.user_id).count() > 0:
        DEMO_MARKER.parent.mkdir(parents=True, exist_ok=True)
        DEMO_MARKER.touch()
        try:
            lock_dir.mkdir(exist_ok=True)
        except Exception:
            pass
        return True
    return False


def seed_demo_data(db: Session) -> bool:
    """Populate sample assistants, knowledge, and a workflow on a fresh install."""
    if _already_seeded(db):
        return False

    # Atomic folder lock to prevent uvicorn multi-worker startup races
    lock_dir = DATA_DIR / ".demo_seeded_lock"
    try:
        lock_dir.mkdir(exist_ok=False)
    except FileExistsError:
        return False

    admin = db.query(User).filter(User.user_name == "admin").first()
    if not admin:
        try:
            lock_dir.rmdir()
        except Exception:
            pass
        return False

    ws = ensure_personal_workspace(db, admin)
    wid = ws.id

    if not db.query(User).filter(User.user_name == "demo").first():
        demo_user = User(user_name="demo", password=hash_password("demo123"), role="viewer")
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
        desc="Answers support and policy questions using the product handbook.",
        prompt=(
            "You are the Senior Customer Experience Specialist for NovaFlow AI. Your mission is to provide accurate, "
            "comprehensive, and friendly support. Always base your answers directly on the retrieved context (from the handbook "
            "or product database). Include citations where appropriate. If the retrieved documentation does not contain enough "
            "information to resolve the user's issue, explain this clearly and instruct them to contact support@novaflow.ai directly."
        ),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
    )
    docs = Assistant(
        name="Document Q&A",
        desc="Synthesizes, summarizes, and extracts insights from uploaded documents.",
        prompt=(
            "You are an advanced Document Synthesis & Intelligence Engine. Analyze all retrieved documents to extract "
            "key insights, actionable takeaways, and structured summaries. When citing sources, refer to the document "
            "name and chunk segment. Remain strictly objective and factual."
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
    
    # Seed 6 developer-centric, tool-equipped agents for companies
    agent1 = SavedAgent(
        id=uuid.uuid4().hex,
        name="GitHub Pull Request & Issue Reviewer",
        desc="Inspects code submissions, peeks files, writes refactored patches, and executes test suites to review PRs.",
        system_prompt=(
            "You are a Senior Software Engineer & Code Reviewer. Inspect code submissions, PR diffs, and issue reports. "
            "Use dir_list and file_peek to view and analyze codebase files. Use file_write to apply code refactors or write "
            "reviews to disk. Use shell_run to run test suites (like pytest) and verify your changes. Use regex_extract to capture issue numbers. "
            "Write highly detailed code reviews: identify bugs first, then suggest clean markdown refactoring."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "regex_extract"]),
        knowledge_id=kb.id,
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    agent2 = SavedAgent(
        id=uuid.uuid4().hex,
        name="DevOps & Incident Responder",
        desc="Parses server logs, peeks server configurations, writes incident summaries, and executes system diagnostics.",
        system_prompt=(
            "You are a DevOps & Site Reliability Engineer. When an incident alert occurs, inspect files and logs using dir_list "
            "and file_peek. Use file_write to log incident summaries or update configuration parameters. Use shell_run to run "
            "system diagnostic commands, check network configs, or parse logs. Parse JSON configurations using json_parse."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "json_parse"]),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    agent3 = SavedAgent(
        id=uuid.uuid4().hex,
        name="Database Schema & SQL Optimizer",
        desc="Analyzes database schemas, peeks DDL scripts, writes migration SQL files, and executes query explain plans.",
        system_prompt=(
            "You are a Principal Database Administrator & SQL Performance Architect. Inspect database schemas, migration scripts, "
            "and slow query files using dir_list and file_peek. Use file_write to save optimized SQL migrations to disk. Use "
            "shell_run to run explain queries, check mysql logs, or test database connectivity. Ground queries in knowledge bases "
            "using kb_search."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "kb_search"]),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    agent4 = SavedAgent(
        id=uuid.uuid4().hex,
        name="API Integration & Webhook Engineer",
        desc="Inspects API routes, peeks third-party connector code, writes request payloads, and executes test endpoints.",
        system_prompt=(
            "You are a Senior API Integration & Backend Engineer. Your task is to audit external integrations, API schemas, "
            "and webhook endpoints. Use dir_list and file_peek to inspect connector folders and routing code. Use file_write "
            "to write modified endpoint configurations. Use shell_run to execute curls, run backend tests, or verify server "
            "routing. Parse JSON payloads using json_parse."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "json_parse"]),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    agent5 = SavedAgent(
        id=uuid.uuid4().hex,
        name="Security & Dependency Auditor",
        desc="Scans package files, lockfiles, and configuration files for outdated libraries, writing patch files.",
        system_prompt=(
            "You are a Cybersecurity & DevSecOps Auditor. Scan workspace dependencies, library versions, and configuration files. "
            "Use dir_list and file_peek to read files like requirements.txt, package.json, and lockfiles. Use file_write to write "
            "updated requirements or lock file patches. Use shell_run to run security audit scanners, check pip status, or run "
            "vulnerability tests. Fetch database URLs using web_fetch."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "web_fetch"]),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    agent6 = SavedAgent(
        id=uuid.uuid4().hex,
        name="Log Parser & Performance Analyst",
        desc="Inspects server logs, analyzes profiling traces, writes optimization reports, and executes benchmark commands.",
        system_prompt=(
            "You are a Principal Performance Engineer. Analyze execution logs, profile summaries, and latency traces to find bottlenecks. "
            "Use dir_list and file_peek to read logs or trace reports. Use file_write to output benchmark reports. Use shell_run to "
            "execute latency test scripts, trigger profiling runs, or compile benchmarks. Extract details using regex_extract."
        ),
        tools_json=json.dumps(["file_peek", "dir_list", "file_write", "shell_run", "regex_extract"]),
        user_id=admin.user_id,
        workspace_id=wid,
        status=1,
        agent_type="custom",
        lifecycle_status="published",
    )
    db.add(agent1)
    db.add(agent2)
    db.add(agent3)
    db.add(agent4)
    db.add(agent5)
    db.add(agent6)
    db.commit()

    DEMO_MARKER.parent.mkdir(parents=True, exist_ok=True)
    DEMO_MARKER.touch()
    print("[NovaFlow] Demo data seeded — assistants, knowledge, and workflow ready.")
    return True
