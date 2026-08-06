import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_smoke import _auth_headers


@pytest.fixture
def api_client():
    """Local FastAPI client — avoid pytest-django's `client` fixture."""
    with TestClient(app) as c:
        yield c


def test_conversation_attachment_upload_and_list(api_client):
    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Upload test", "conversation_type": "assistant"},
    ).json()["data"]
    conv_id = conv["id"]

    files = {"file": ("notes.txt", io.BytesIO(b"hello attachment context"), "text/plain")}
    up = api_client.post(
        f"/api/v1/conversations/{conv_id}/attachments",
        headers=headers,
        files=files,
    )
    assert up.status_code == 200
    body = up.json()
    assert body["status_code"] == 200
    assert body["data"]["attachment_id"]
    assert body["data"]["has_extracted_text"] is True

    listed = api_client.get(f"/api/v1/conversations/{conv_id}/attachments", headers=headers)
    assert listed.status_code == 200
    rows = listed.json()["data"]
    assert len(rows) >= 1


def test_deploy_creates_workflow(api_client):
    headers = _auth_headers(api_client)
    compile_res = api_client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "Build workflow automation for customer support"},
    )
    assert compile_res.status_code == 200
    data = compile_res.json()["data"]
    solution_id = data["solution_id"]
    assert solution_id

    from app.database import SessionLocal, Workflow

    db = SessionLocal()
    try:
        before = db.query(Workflow).count()
    finally:
        db.close()

    from app.composer.deployment import deploy_solution_graph
    from app.database import SessionLocal as SL

    db = SL()
    try:
        report = deploy_solution_graph(db, workspace_id=1, solution_id=solution_id, user_id=1)
    finally:
        db.close()

    assert report["workflow_id"]
    db = SL()
    try:
        after = db.query(Workflow).count()
        wf = db.get(Workflow, report["workflow_id"])
    finally:
        db.close()
    assert after >= before + 1
    assert wf is not None
    assert wf.status == 1


def test_telegram_knowledge_graph_shape():
    from app.composer.workflow_composer import build_executable_graph

    graph = build_executable_graph(
        required_caps=["cap_telegram", "cap_knowledge"],
        goal="Build a telegram support bot that answers from knowledge",
        knowledge_id=42,
    )
    types = [n["type"] for n in graph["nodes"]]
    assert types[0] == "trigger"
    assert "retrieve" in types
    assert "llm" in types
    assert "notify" in types
    assert "output" in types
    notify = next(n for n in graph["nodes"] if n["type"] == "notify")
    assert notify["data"]["channel"] == "telegram"


def test_intent_router_keywords():
    from app.composer.chat_bridge import classify_intent

    assert classify_intent("build a telegram support bot that answers from knowledge") == "compose"
    assert classify_intent("approve", has_pending=True) == "approve"
    assert classify_intent("run test", has_pending=True) == "test"
    assert classify_intent("deploy this", has_pending=True) == "deploy"
    assert classify_intent("cancel", has_pending=True) == "cancel"
    assert classify_intent("what is the weather?") == "chat"


def test_compose_approve_deploy_bridge_flow(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import Conversation, SessionLocal, Workflow

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "AIOS bridge", "conversation_type": "assistant"},
    ).json()["data"]
    conv_id = conv["id"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="Build a telegram support bot that answers from knowledge",
        )
        assert compose["blocked_normal_reply"] is True
        types = [e["type"] for e in compose["events"]]
        assert "aios_solution" in types
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        assert sol.get("phase") == "blueprint" or sol.get("status") == "blueprint"
        assert not sol.get("solution_id")
        assert "telegram_bot_token" in (sol.get("missing_credentials") or [])
        node_types = sol.get("node_types") or []
        assert "retrieve" in node_types or "notify" in node_types

        # Deploy blocked before approve
        blocked = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="deploy",
        )
        assert not any(e["type"] == "aios_deploy" and e["data"].get("workflow_id") for e in blocked["events"])

        from app.services import credential_vault as vault

        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="telegram",
            kind="telegram_bot",
            label="default",
            fields={"bot_token": "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"},
        )

        approve = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="approve",
        )
        atypes = [e["type"] for e in approve["events"]]
        assert "aios_approved" in atypes
        assert "aios_test_report" in atypes
        report = next(e for e in approve["events"] if e["type"] == "aios_test_report")["data"]
        assert report.get("status") in ("success", "failed")
        assert report.get("node_count", 0) >= 3

        before = db.query(Workflow).count()
        deploy = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="deploy",
        )
        assert any(e["type"] == "aios_deploy" for e in deploy["events"])
        dep = next(e for e in deploy["events"] if e["type"] == "aios_deploy")["data"]
        assert dep.get("workflow_id")
        after = db.query(Workflow).count()
        assert after >= before + 1
        wf = db.get(Workflow, dep["workflow_id"])
        assert wf is not None
        graph = json.loads(wf.graph_json or "{}")
        wf_types = [n.get("type") for n in (graph.get("nodes") or [])]
        assert "notify" in wf_types
        assert "retrieve" in wf_types

        row = db.get(Conversation, conv_id)
        meta = json.loads(row.meta_json or "{}")
        assert meta.get("aios", {}).get("approved") is True
        assert meta.get("aios", {}).get("status") == "deployed"
    finally:
        db.close()


def test_gap_analysis_prefers_vault(api_client):
    from app.composer.gap_analysis import analyze_solution_gaps
    from app.database import SessionLocal
    from app.services import credential_vault as vault

    _ = api_client  # ensure app/DB seed from fixture path
    db = SessionLocal()
    try:
        missing_before = analyze_solution_gaps(db, 1, ["cap_telegram"])
        assert "telegram_bot_token" in missing_before

        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="telegram",
            kind="telegram_bot",
            label="default",
            fields={"bot_token": "1234567890:AAFakeTelegramBotTokenForTestsXXXX"},
        )
        missing_after = analyze_solution_gaps(db, 1, ["cap_telegram"])
        assert "telegram_bot_token" not in missing_after
    finally:
        db.close()


def test_vague_goal_clarify(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "clarify", "conversation_type": "assistant"},
    ).json()["data"]
    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="automate my work",
        )
        assert out["blocked_normal_reply"] is True
        assert any(e["type"] == "aios_clarify" for e in out["events"])
    finally:
        db.close()


def test_digest_and_github_graph_shapes():
    from app.composer.workflow_composer import build_executable_graph

    digest = build_executable_graph(
        required_caps=["cap_smtp", "cap_knowledge"],
        goal="Create a weekly email digest from my documents",
    )
    dtypes = [n["type"] for n in digest["nodes"]]
    assert "retrieve" in dtypes
    assert "notify" in dtypes
    notify = next(n for n in digest["nodes"] if n["type"] == "notify")
    assert notify["data"]["channel"] == "email"

    gh = build_executable_graph(
        required_caps=["cap_github"],
        goal="Build a GitHub issue triage workflow",
    )
    gtypes = [n["type"] for n in gh["nodes"]]
    assert "github" in gtypes
    assert "output" in gtypes


def test_agent_os_plan_in_meta(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import Conversation, SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "agent os", "conversation_type": "assistant"},
    ).json()["data"]
    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Create a multi-agent research supervisor that asks me before acting",
        )
        types = [e["type"] for e in out["events"]]
        assert "aios_solution" in types
        assert any(e["type"] in ("aios_hitl", "aios_progress") for e in out["events"])
        row = db.get(Conversation, conv["id"])
        meta = json.loads(row.meta_json or "{}")
        agent_os = (meta.get("aios") or {}).get("agent_os") or {}
        assert agent_os.get("plan_session_id")
        assert agent_os.get("run_id")
        assert agent_os.get("tasks")
    finally:
        db.close()


def test_heal_after_sandbox_failure():
    from app.composer.chat_advanced import heal_and_retest

    broken = {"nodes": [{"id": "trigger", "type": "trigger", "data": {}}], "edges": []}
    healed, report, fixes = heal_and_retest(broken, missing_credentials=[])
    assert "output" in [(n.get("type") if isinstance(n, dict) else None) for n in healed["nodes"]]
    assert fixes
    assert report.get("status") in ("success", "failed")


def test_host_boundary():
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=None,
            user_message="please control my PC and open chrome",
        )
        assert out["blocked_normal_reply"] is True
        assert any(e["type"] == "aios_clarify" and e["data"].get("boundary") for e in out["events"])
    finally:
        db.close()


def test_process_chat_turn_capabilities(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "caps", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            return await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="What can you do?",
            )
        finally:
            db.close()

    out = anyio.run(_run)
    assert out["blocked_normal_reply"] is True
    assert any(e["type"] == "aios_capabilities" for e in out["events"])


def test_process_chat_turn_list_workflows(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.database import SessionLocal, Workflow

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "list wf", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            wf = Workflow(
                id="wf_chat_super_list",
                workspace_id=1,
                name="Chat Super List WF",
                desc="seed",
                graph_json=json.dumps(
                    {
                        "nodes": [
                            {"id": "t", "type": "trigger", "data": {}},
                            {"id": "o", "type": "output", "data": {}},
                        ],
                        "edges": [{"source": "t", "target": "o"}],
                    }
                ),
                status=1,
                user_id=1,
            )
            db.merge(wf)
            db.commit()
            return await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="List my workflows",
            )
        finally:
            db.close()

    out = anyio.run(_run)
    assert out["blocked_normal_reply"] is True
    ev = next(e for e in out["events"] if e["type"] == "aios_workflows")
    assert ev["data"]["count"] >= 1
    assert any(w["id"] == "wf_chat_super_list" for w in ev["data"]["workflows"])


def test_heal_ask_after_one_heal(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import Conversation, SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "heal ask", "conversation_type": "assistant"},
    ).json()["data"]
    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build a telegram support bot that answers from knowledge",
        )
        assert any(e["type"] == "aios_solution" for e in compose["events"])
        process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="approve",
        )
        row = db.get(Conversation, conv["id"])
        meta = json.loads(row.meta_json or "{}")
        heal_count = int((meta.get("aios") or {}).get("heal_count") or 0)
        # Ensure at least one heal consumed (approve may auto-heal)
        if heal_count < 1:
            process_chat_goal(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="heal",
            )
            row = db.get(Conversation, conv["id"])
            meta = json.loads(row.meta_json or "{}")
            assert int((meta.get("aios") or {}).get("heal_count") or 0) >= 1

        ask = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="heal",
        )
        heal_ev = next(e for e in ask["events"] if e["type"] == "aios_heal")
        assert heal_ev["data"]["status"] == "ask"
    finally:
        db.close()


def test_voice_intent_commands():
    from app.voice.service import VoiceService

    vs = VoiceService()
    assert vs.classify_intent("approve").action == "suggest"
    assert vs.classify_intent("approve").params.get("phrase") == "approve"
    assert vs.classify_intent("deploy").params.get("phrase") == "deploy"
    assert vs.classify_intent("run my last workflow").params.get("phrase") == "Run my last workflow"
    nav = vs.classify_intent("navigate to credentials")
    assert nav.action == "navigate"
    assert nav.target == "/credentials"
    assert vs.classify_intent("what is the weather today").action == "chat"
    assert vs.classify_intent("workspace health").params.get("phrase") == "Workspace health"
    assert vs.classify_intent("list schedules").params.get("phrase") == "List schedules"


def test_enterprise_ops_intents():
    from app.composer.chat_actions import classify_ops_intent
    from app.composer.chat_enterprise import parse_natural_cron

    assert classify_ops_intent("List schedules") == "list_schedules"
    assert classify_ops_intent("Schedule my last workflow daily at 9am") == "schedule_create"
    assert classify_ops_intent("Compliance report") == "compliance_report"
    assert classify_ops_intent("FinOps summary") == "finops_summary"
    assert classify_ops_intent("Workspace health") == "workspace_health"
    assert classify_ops_intent("Show recommendations") == "list_recommendations"
    assert classify_ops_intent("Export this chat as markdown") == "export_conversation"
    assert classify_ops_intent("Share this chat read-only for 72h") == "share_conversation"
    assert classify_ops_intent("Show my recent chat actions") == "audit_trail"
    assert classify_ops_intent("List vault categories") == "vault_posture"
    assert classify_ops_intent("Check Slack/Telegram status") == "integrations_health"
    assert classify_ops_intent("Run incident playbook") == "playbook"
    assert classify_ops_intent("Enterprise playbooks") == "playbook"
    assert parse_natural_cron("daily at 9am") == "0 9 * * *"
    assert parse_natural_cron("every hour") == "0 * * * *"


def test_enterprise_process_chat_turn_ops(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.database import SessionLocal, Workflow, WorkflowSchedule

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "enterprise ops", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            wf = Workflow(
                id="wf_ent_sched",
                workspace_id=1,
                name="Enterprise Sched WF",
                desc="seed",
                graph_json=json.dumps(
                    {
                        "nodes": [
                            {"id": "t", "type": "trigger", "data": {}},
                            {"id": "o", "type": "output", "data": {}},
                        ],
                        "edges": [{"source": "t", "target": "o"}],
                    }
                ),
                status=1,
                user_id=1,
            )
            db.merge(wf)
            db.commit()
            row = WorkflowSchedule(
                workflow_id=wf.id,
                workspace_id=1,
                user_id=1,
                cron_expression="0 9 * * *",
                input_text="seed",
                enabled=1,
            )
            db.add(row)
            db.commit()

            caps = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="What can you do?",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_capabilities" for e in caps["events"])
            skills = next(e for e in caps["events"] if e["type"] == "aios_capabilities")["data"]["skills"]
            assert any("Schedule" in s or "playbook" in s.lower() or "FinOps" in s for s in skills)

            sched = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="List schedules",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_schedule" for e in sched["events"])

            health = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Workspace health",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_health" for e in health["events"])

            finops = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="FinOps summary",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_finops" for e in finops["events"])

            compliance = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Compliance report",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_compliance" for e in compliance["events"])

            export = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Export this chat as markdown",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_export" for e in export["events"])

            share = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Share this chat read-only for 72h",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_share" for e in share["events"])

            play = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Run incident playbook",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_playbook" for e in play["events"])

            denied = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Export this chat as markdown",
                workspace_role="viewer",
            )
            assert any(e["type"] == "aios_denied" for e in denied["events"])
            return True
        finally:
            db.close()

    assert anyio.run(_run) is True


def test_rbac_gate_denied():
    from app.composer.chat_enterprise import gate_role

    out = gate_role("viewer", "schedule_create")
    assert out is not None
    assert out["events"][0]["type"] == "aios_denied"
    assert gate_role("editor", "schedule_create") is None


def test_universal_router_labels():
    from app.composer.chat_router import universal_route

    assert universal_route("List my workflows")["route"] == "ops"
    assert universal_route("What is RAG?")["route"] == "qa"
    work = universal_route("Automate invoice reminders from my documents every Monday")
    assert work["route"] == "work_compose"
    assert universal_route("Create a multi-agent research supervisor that asks me before acting")["route"] == "agent"
    assert universal_route("please control my PC and open chrome")["route"] == "boundary"


def test_vague_field_clarify(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    _ = api_client
    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=None,
            user_message="automate my work",
        )
        assert out["blocked_normal_reply"] is True
        clarify = next(e for e in out["events"] if e["type"] == "aios_clarify")
        assert clarify["data"].get("clarify_kind") == "field" or any(
            "Field" in q for q in (clarify["data"].get("questions") or [])
        )
    finally:
        db.close()


def test_unknown_domain_invoice_compose(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "invoice domain", "conversation_type": "assistant"},
    ).json()["data"]
    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Automate invoice approval emails from my docs",
        )
        assert out["blocked_normal_reply"] is True
        sol = next(e for e in out["events"] if e["type"] == "aios_solution")
        nodes = (sol["data"].get("executable_preview") or {}).get("nodes") or []
        types = [n.get("type") for n in nodes if isinstance(n, dict)]
        assert "trigger" in types
        assert "llm" in types or "agent" in types
        assert "output" in types
        assert sol["data"].get("last_field") in ("finance", "generic", "ops", "support", "hr", "sales", "content")
    finally:
        db.close()


def test_hr_onboarding_compose(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "hr domain", "conversation_type": "assistant"},
    ).json()["data"]
    db = SessionLocal()
    try:
        out = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Onboard new hires with a welcome email",
        )
        assert any(e["type"] == "aios_solution" for e in out["events"])
        sol = next(e for e in out["events"] if e["type"] == "aios_solution")
        recipe = sol["data"].get("recipe") or {}
        assert recipe.get("id") in ("hr_onboarding", "email_digest", "generic_automation") or sol[
            "data"
        ].get("last_field") in ("hr", "generic", "finance")
        types = sol["data"].get("node_types") or []
        assert len(types) >= 3
    finally:
        db.close()


def test_generic_fallback_graph_shape():
    from app.composer.workflow_composer import build_executable_graph

    graph = build_executable_graph(required_caps=[], goal="Do something useful with my ops notes")
    types = [n["type"] for n in graph["nodes"]]
    assert types[0] == "trigger"
    assert "llm" in types or "agent" in types
    assert types[-1] == "output"
    assert (graph.get("meta") or {}).get("recipe_id") in (None, "generic_automation", "ops_status_report", "content_draft")


def test_capture_and_fulfill_requirements(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.composer.chat_requirements import check_chat_policy, parse_requirements
    from app.database import PlatformPolicy, SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "req fulfill", "conversation_type": "assistant"},
    ).json()["data"]

    req = parse_requirements("Onboard new hires with a welcome email within 24 hours")
    assert req["field"] == "hr"
    assert req["output"] == "email"
    assert req["checklist"]

    async def _run():
        db = SessionLocal()
        try:
            cap = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Capture requirements: onboard new hires with welcome email",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_requirements" for e in cap["events"])

            show = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Show requirements",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_requirements" for e in show["events"])

            fulfill = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Fulfill these requirements",
                workspace_role="editor",
            )
            types = [e["type"] for e in fulfill["events"]]
            assert "aios_solution" in types
            assert "aios_fulfillment" in types

            # Policy deny
            row = PlatformPolicy(
                workspace_id=1,
                policy_type="chat",
                scope="workspace",
                rule_key="chat.block_run",
                rule_value="Maintenance freeze",
                severity="enforce",
                enabled=1,
            )
            db.add(row)
            db.commit()
            blocked = check_chat_policy(db, workspace_id=1, action="run_workflow")
            assert blocked is not None
            assert blocked["events"][0]["type"] == "aios_policy"
            return True
        finally:
            db.close()

    assert anyio.run(_run) is True


def test_requirements_ops_intents():
    from app.composer.chat_actions import classify_ops_intent

    assert classify_ops_intent("Capture requirements: do the thing") == "capture_requirements"
    assert classify_ops_intent("Show requirements") == "show_requirements"
    assert classify_ops_intent("Fulfill these requirements") == "fulfill_requirements"
    assert classify_ops_intent("Show chat policy") == "show_policy"


def test_powerhouse_intent_classification():
    from app.composer.chat_powerhouse import POWER_INTENTS, classify_power_intent

    mapping = {
        "Show powerhouse": "powerhouse_catalog",
        "Diff my workflow": "workflow_diff",
        "Show workflow versions": "version_time_machine",
        "Restore version #2": "restore_version",
        "Eval scorecard": "eval_command",
        "Show cost receipt": "cost_receipt",
        "Debug last run": "run_debugger",
        "Explore knowledge graph": "knowledge_graph",
        "Open collab war room": "collab_war_room",
        "Confirm kill switch": "incident_kill_switch",
        "Run simulation lab": "simulate_lab",
        "SLA reliability brief": "sla_brief",
        "Propose change: add Slack notify": "change_request",
        "Apply change request": "apply_change_request",
        "Digest attachments to workflows": "action_digest",
    }
    for phrase, intent in mapping.items():
        assert classify_power_intent(phrase) == intent, phrase
        assert intent in POWER_INTENTS


def test_powerhouse_catalog_and_handlers(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.composer.chat_powerhouse import powerhouse_catalog_action
    from app.database import SessionLocal
    from app.sandbox.enterprise_suite import run_simulation_matrix as suite_matrix

    cat = powerhouse_catalog_action()
    assert cat["events"][0]["type"] == "aios_powerhouse"
    assert len(cat["events"][0]["data"]["tools"]) >= 12

    # simulation matrix unit
    good = {
        "nodes": [
            {"id": "trigger", "type": "trigger"},
            {"id": "llm", "type": "llm"},
            {"id": "output", "type": "output"},
        ],
        "edges": [{"from": "trigger", "to": "llm"}, {"from": "llm", "to": "output"}],
        "meta": {"node_types": ["trigger", "llm", "output"]},
    }
    matrix = suite_matrix(good, fields=["finance", "hr", "generic"])
    assert matrix["field_count"] == 3
    assert matrix["passed_fields"] >= 1

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Powerhouse", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            catalog = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Show powerhouse",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_powerhouse" for e in catalog["events"])

            receipt = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Show cost receipt",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_receipt" for e in receipt["events"])

            sla = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="SLA reliability brief",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_sla" for e in sla["events"])

            kill = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Kill switch",
                workspace_role="editor",
            )
            inc = next(e for e in kill["events"] if e["type"] == "aios_incident")
            assert inc["data"]["status"] == "confirm_required"

            # compose then simulate
            compose = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Automate invoice reminders from my documents every Monday",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_solution" for e in compose["events"])

            sim = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Run simulation lab",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_simulate" for e in sim["events"])

            diff = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Diff my workflow",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_diff" for e in diff["events"])

            return True
        finally:
            db.close()

    assert anyio.run(_run) is True


def test_enterprise_suite_structural():
    from app.sandbox.enterprise_suite import run_enterprise_suite

    broken = run_enterprise_suite({"nodes": [], "edges": []})
    assert broken["status"] == "failed"
    assert broken["failed"] >= 1
    assert any(c["id"] == "structural" and c["status"] == "failed" for c in broken["checks"])

    good = {
        "nodes": [
            {"id": "trigger", "type": "trigger"},
            {"id": "llm", "type": "llm"},
            {"id": "output", "type": "output"},
        ],
        "edges": [
            {"from": "trigger", "to": "llm"},
            {"from": "llm", "to": "output"},
        ],
        "meta": {"node_types": ["trigger", "llm", "output"]},
    }
    ok_report = run_enterprise_suite(good, field="finance")
    assert ok_report["status"] == "success"
    assert ok_report["suite"] == "enterprise"
    assert ok_report["passed"] >= 3


def test_chat_upload_ceiling_rejects_oversize(api_client):
    from app.security.config import MAX_CHAT_UPLOAD_BYTES

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "GB ceiling", "conversation_type": "assistant"},
    ).json()["data"]
    conv_id = conv["id"]
    over = MAX_CHAT_UPLOAD_BYTES + 1
    init = api_client.post(
        f"/api/v1/conversations/{conv_id}/attachments/chunk-init",
        headers=headers,
        json={
            "file_name": "huge.csv",
            "file_size": over,
            "chunk_size": 8 * 1024 * 1024,
            "total_chunks": max(1, (over + 8 * 1024 * 1024 - 1) // (8 * 1024 * 1024)),
        },
    )
    assert init.status_code == 200
    body = init.json()
    assert body["status_code"] == 400
    assert "exceeds" in (body.get("status_message") or body.get("detail") or "").lower() or "exceeds" in str(
        body
    ).lower()


def test_express_compose_emits_sandbox(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Express compose", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            out = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Automate invoice reminders from my documents every Monday",
                workspace_role="editor",
            )
            types = [e["type"] for e in out["events"]]
            ui = out.get("ui_events") or []
            assert len(ui) == 1
            assert ui[0]["type"] in ("aios_solution", "aios_sandbox")
            # Full audit events may still include solution; UI is one card
            assert "aios_solution" in types or "aios_sandbox" in types
            primary = out.get("primary_event") or ui[0]
            assert primary.get("data", {}).get("compose_ms") is not None or primary.get("data", {}).get(
                "express"
            ) is not None or primary["type"] == "aios_solution"
            return True
        finally:
            db.close()

    assert anyio.run(_run) is True

def test_friendly_summary_no_uuid_and_email_goal():
    from app.composer.chat_narrative import friendly_summary
    from app.voice.service import polish_transcript

    events = [
        {
            "type": "aios_solution",
            "data": {
                "solution_id": "cba695b62ffb47e7aee3e915fe1cef58",
                "recipe_name": "Generic Field Automation",
                "node_types": ["trigger", "llm", "notify", "output"],
                "missing_credentials": ["smtp_password"],
                "goal": "send emails daily to kishorevekariya70@gmail.com government",
            },
        },
        {"type": "aios_credentials_needed", "data": {"missing": ["smtp_password"]}},
        {"type": "aios_progress", "data": {"next_action": "credentials"}},
    ]
    text = friendly_summary(
        events,
        goal="hello my name is Ansh and I need to send emails daily on this subject on kishorevekariya70@gmail.com government",
    )
    assert "cba695b62ffb47e7aee3e915fe1cef58" not in text
    assert "Generic Field Automation" not in text
    assert "kishorevekariya70@gmail.com" in text
    assert "email password" in text.lower() or "smtp" not in text.lower()
    assert "Approve" in text or "Credentials" in text or "credential" in text.lower()

    polished = polish_transcript("please impliment it for mr")
    assert "implement" in polished.lower()
    assert "for me" in polished.lower()

    email_polished = polish_transcript(
        "send daily email to kishore at gmail dot com about government updates"
    )
    assert "kishore@gmail.com" in email_polished.lower()


def test_nl_credential_extract_gmail_app_password():
    from app.composer.chat_bridge import (
        _extract_credential_updates,
        _select_primary_event,
        _ui_events_from,
        looks_like_secret_message,
        redact_secrets_in_text,
    )

    items = _extract_credential_updates(
        "my email is smtp.user@example.com and its pass is abcd efgh ijkl mnop"
    )
    assert items
    fields = items[0]["fields"]
    assert fields.get("smtp_user") == "smtp.user@example.com"
    assert fields.get("smtp_password") == "abcdefghijklmnop"
    assert looks_like_secret_message("abcd efgh ijkl mnop")
    bare = _extract_credential_updates("abcd efgh ijkl mnop")
    assert bare and bare[0]["fields"].get("smtp_password") == "abcdefghijklmnop"

    key_items = _extract_credential_updates(
        "the llm api key is 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"
    )
    assert key_items
    assert "sk-or-v1-" in key_items[0]["fields"].get("api_key", "")

    redacted = redact_secrets_in_text(
        "pass is abcd efgh ijkl mnop and sk-or-v1-aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ["abcd efgh ijkl mnop"],
    )
    assert "whli jwom" not in redacted
    assert "sk-or-v1-" not in redacted

    events = [
        {"type": "aios_memory", "data": {"last_recipe": "x"}},
        {"type": "aios_progress", "data": {"next_action": "approve"}},
        {"type": "aios_solution", "data": {"solution_id": "abc", "status": "pending_approval"}},
        {"type": "aios_fulfillment", "data": {"message": "Working checklist"}},
    ]
    primary = _select_primary_event(events)
    assert primary["type"] == "aios_solution"
    ui = _ui_events_from(events)
    assert len(ui) == 1
    assert ui[0]["type"] == "aios_solution"


def test_vault_smtp_clears_gap_and_nl_save(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_goal
    from app.composer.gap_analysis import analyze_solution_gaps
    from app.database import SessionLocal
    from app.services import credential_vault as vault

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Cred unity", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="email",
            kind="gmail_smtp",
            label="default",
            fields={
                "smtp_user": "smtp.user@example.com",
                "smtp_password": "abcdefghijklmnop",
                "smtp_host": "smtp.gmail.com",
            },
        )
        missing = analyze_solution_gaps(db, 1, ["cap_smtp"])
        assert missing == []

        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="send daily email to friend@example.com about government updates",
        )
        assert compose["blocked_normal_reply"] is True
        ui = compose.get("ui_events") or []
        assert len(ui) == 1
        primary = compose.get("primary_event") or ui[0]
        assert primary["type"] in ("aios_solution", "aios_sandbox")
        data = primary.get("data") or {}
        assert "smtp_password" not in (data.get("missing_credentials") or [])
        assert "Generic Field Automation" not in (compose.get("summary") or "")
    finally:
        db.close()

    async def _paste():
        db2 = SessionLocal()
        try:
            from app.composer.chat_bridge import process_chat_turn

            # Fresh conversation without pre-seeded vault for paste path
            conv2 = api_client.post(
                "/api/v1/conversations",
                headers=headers,
                json={"title": "Paste creds", "conversation_type": "assistant"},
            ).json()["data"]
            await process_chat_turn(
                db2,
                workspace_id=1,
                user_id=1,
                conversation_id=conv2["id"],
                user_message="Build a workflow to email daily updates to peer@gmail.com",
                workspace_role="editor",
            )
            saved = await process_chat_turn(
                db2,
                workspace_id=1,
                user_id=1,
                conversation_id=conv2["id"],
                user_message="my email is smtp.user@example.com and its pass is abcd efgh ijkl mnop",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_credentials_saved" for e in saved["events"])
            assert len(saved.get("ui_events") or [saved.get("primary_event")]) == 1
            assert "REDACTED" in (saved.get("redacted_message") or "") or "abcd" not in (
                saved.get("redacted_message") or ""
            )
            return True
        finally:
            db2.close()

    assert anyio.run(_paste) is True


def test_ops_registry_bootstrap():
    from app.composer.chat_ops_registry import catalog_tools, ensure_ops_bootstrapped, list_ops

    ensure_ops_bootstrapped()
    groups = {op.catalog_group for op in list_ops()}
    assert "powerhouse" in groups
    assert "autopilot" in groups
    assert "forge" in groups
    assert len(catalog_tools("powerhouse")) >= 12
    assert len(catalog_tools("forge")) >= 12


def test_autopilot_intent_classification():
    from app.composer.chat_autopilot import AUTOPILOT_INTENTS, classify_autopilot_intent

    mapping = {
        "Run incident autopilot": "autopilot_start",
        "Confirm autopilot": "autopilot_confirm",
        "Autopilot status": "autopilot_status",
        "Cancel autopilot": "autopilot_cancel",
        "Skip autopilot step": "autopilot_skip",
    }
    for phrase, intent in mapping.items():
        assert classify_autopilot_intent(phrase) == intent
        assert intent in AUTOPILOT_INTENTS


def test_forge_intent_classification():
    from app.composer.chat_forge import FORGE_INTENTS, classify_forge_intent

    mapping = {
        "Show forge": "forge_catalog",
        "Show prompt drift": "prompt_drift",
        "Show A/B routes": "ab_router",
        "Open webhook studio": "webhook_studio",
        "List project packs": "project_packs",
        "Scan for publish": "publish_scan",
        "Find reusable template": "template_reuse",
        "Model lab costs": "model_lab_desk",
        "OCR attachments to workflow": "ocr_to_workflow",
        "GitHub issue bridge": "issue_bridge",
        "Import CSV from chat": "csv_import_chat",
        "Generate solution docs": "solution_docs",
        "Run solution assertions": "solution_assert",
    }
    for phrase, intent in mapping.items():
        assert classify_forge_intent(phrase) == intent
        assert intent in FORGE_INTENTS


def test_autopilot_and_forge_handlers(api_client):
    import anyio
    from app.composer.chat_bridge import process_chat_turn
    from app.composer.chat_forge import forge_catalog_action
    from app.database import SessionLocal

    cat = forge_catalog_action()
    assert cat["events"][0]["type"] == "aios_forge"
    assert len(cat["events"][0]["data"]["tools"]) >= 12

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "God tier", "conversation_type": "assistant"},
    ).json()["data"]

    async def _run():
        db = SessionLocal()
        try:
            autopilot = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Run incident autopilot",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_autopilot" for e in autopilot["events"])

            forge = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Show forge",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_forge" for e in forge["events"])

            drift = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Show prompt drift",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_drift" for e in drift["events"])

            cancel = await process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Cancel autopilot",
                workspace_role="editor",
            )
            assert any(e["type"] == "aios_autopilot" for e in cancel["events"])

            return True
        finally:
            db.close()

    assert anyio.run(_run) is True


def test_universal_channel_detect_and_titles():
    from app.composer.chat_channels import (
        detect_channels,
        extract_channel_credentials,
        friendly_title_for_goal,
        looks_like_channel_secret,
    )

    ids = {c.id for c in detect_channels("sync Shopify orders to Slack")}
    assert {"shopify", "slack"} <= ids
    assert any(c.id == "google" for c in detect_channels("connect Google Sheets via Google OAuth"))
    assert any(c.id == "outlook" for c in detect_channels("send Outlook mail every Monday"))
    assert any(c.id == "telegram" for c in detect_channels("build a telegram support bot"))
    assert any(c.id == "custom" for c in detect_channels("automate HubSpot CRM contact sync via API"))
    assert "Shopify" in friendly_title_for_goal("Shopify order alerts")
    hub_title = friendly_title_for_goal("automate HubSpot deal updates")
    assert "Hubspot" in hub_title or "HubSpot" in hub_title

    shop = extract_channel_credentials(
        "shopify shop is mystore.myshopify.com and access token is shpat_abcdefghijklmnopqrstuvwxyz12"
    )
    assert shop and shop[0]["category"] == "shopify"
    assert shop[0]["fields"].get("shop") == "mystore.myshopify.com"
    assert shop[0]["fields"].get("access_token", "").startswith("shpat_")

    goo = extract_channel_credentials(
        "google client_id is cid123 google client_secret is gsec456 google refresh_token is gref789"
    )
    assert goo and goo[0]["category"] == "google"
    assert goo[0]["fields"].get("client_secret") == "gsec456"
    assert goo[0]["fields"].get("refresh_token") == "gref789"

    outl = extract_channel_credentials(
        "outlook client_id is ocid outlook client_secret is osec outlook refresh_token is oref"
    )
    assert outl and outl[0]["category"] == "outlook"
    assert outl[0]["fields"].get("client_secret") == "osec"

    custom = extract_channel_credentials(
        "hubspot api_key is hubspotkey12345 and base_url is https://api.hubapi.com"
    )
    assert custom and custom[0]["category"] == "custom"
    assert custom[0]["fields"].get("api_key") == "hubspotkey12345"
    assert "hubapi.com" in custom[0]["fields"].get("base_url", "")

    assert looks_like_channel_secret("shpat_abcdefghijklmnopqrstuvwxyz12")
    assert looks_like_channel_secret("paste google client_secret: abcdefghijklmnop")


def test_universal_channel_graphs_and_gaps(api_client):
    from app.composer.gap_analysis import analyze_solution_gaps
    from app.composer.workflow_composer import build_executable_graph
    from app.database import SessionLocal
    from app.services import credential_vault as vault

    g_shop = build_executable_graph(
        required_caps=["cap_shopify", "cap_workflow"],
        goal="Sync Shopify orders nightly",
    )
    assert any(n.get("id") == "shopify" for n in g_shop["nodes"])

    g_custom = build_executable_graph(
        required_caps=["cap_http", "cap_workflow"],
        goal="Automate HubSpot CRM sync via API",
    )
    http = next(n for n in g_custom["nodes"] if n.get("type") == "http")
    assert "{{base_url}}" in (http.get("data") or {}).get("url", "")

    g_out = build_executable_graph(
        required_caps=["cap_outlook", "cap_workflow"],
        goal="Send Outlook mail digests",
    )
    assert any(
        n.get("type") == "notify" and (n.get("data") or {}).get("channel") == "email"
        or n.get("type") == "http"
        for n in g_out["nodes"]
    )

    db = SessionLocal()
    try:
        assert "shopify_access_token" in analyze_solution_gaps(db, 1, ["cap_shopify"]) or "shopify_shop" in analyze_solution_gaps(
            db, 1, ["cap_shopify"]
        )
        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="shopify",
            kind="shopify_admin",
            label="default",
            fields={"shop": "demo.myshopify.com", "access_token": "shpat_testdemotoken1234567890"},
        )
        assert analyze_solution_gaps(db, 1, ["cap_shopify"]) == []

        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="google",
            kind="google_oauth",
            label="default",
            fields={"client_id": "cid", "client_secret": "sec", "refresh_token": "rtok"},
        )
        assert analyze_solution_gaps(db, 1, ["cap_google"]) == []

        vault.upsert_from_chat(
            db,
            workspace_id=1,
            user_id=1,
            category="custom",
            kind="custom",
            label="default",
            fields={"api_key": "customkey123456", "base_url": "https://api.example.com"},
        )
        assert analyze_solution_gaps(db, 1, ["cap_http"]) == []
    finally:
        db.close()


def test_universal_compose_shopify_and_google_one_card(api_client):
    from app.composer.chat_bridge import process_chat_goal, _ui_events_from
    from app.database import CredentialVaultEntry, SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Universal pack", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        # Isolate from other tests that seed workspace 1 vault
        db.query(CredentialVaultEntry).filter(
            CredentialVaultEntry.workspace_id == 1,
            CredentialVaultEntry.category.in_(("shopify", "google")),
        ).delete(synchronize_session=False)
        db.commit()

        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build Shopify order sync automation",
        )
        assert compose["blocked_normal_reply"] is True
        ui = compose.get("ui_events") or _ui_events_from(compose["events"])
        assert len(ui) == 1
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        missing = sol.get("missing_credentials") or []
        assert any(m.startswith("shopify") for m in missing)
        assert "Shopify" in (sol.get("friendly_title") or "") or "shopify" in (sol.get("message") or "").lower()

        conv2 = api_client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"title": "Google pack", "conversation_type": "assistant"},
        ).json()["data"]
        gcompose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv2["id"],
            user_message="Connect Google Sheets via Google OAuth and automate updates",
        )
        gsol = next(e for e in gcompose["events"] if e["type"] == "aios_solution")["data"]
        gmiss = gsol.get("missing_credentials") or []
        assert any(m.startswith("google") for m in gmiss)
        assert len(gcompose.get("ui_events") or _ui_events_from(gcompose["events"])) == 1
    finally:
        db.close()


def test_send_emails_diwali_blueprint_then_approve(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.composer.chat_router import universal_route
    from app.database import Conversation, SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Diwali emails", "conversation_type": "assistant"},
    ).json()["data"]

    route = universal_route("I want to send emails on Diwali topic to my friends")
    assert route.get("route") == "work_compose"

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="I want to send emails on Diwali topic to my friends",
        )
        assert compose["blocked_normal_reply"] is True
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        assert sol.get("phase") == "blueprint"
        assert not sol.get("solution_id")
        req = sol.get("requirements") or {}
        assert req.get("email_topic") or "diwali" in (req.get("goal") or "").lower()

        process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="my email is tester@example.com and password is abcd efgh ijkl mnop",
        )

        approve = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="approve",
        )
        assert "aios_approved" in [e["type"] for e in approve["events"]]
        row = db.get(Conversation, conv["id"])
        meta = json.loads(row.meta_json or "{}")
        assert meta.get("aios", {}).get("solution_id")
    finally:
        db.close()


def test_finalize_blocked_has_summary(api_client):
    from app.composer.chat_bridge import _finalize

    _ = api_client
    out = _finalize(
        [{"type": "aios_solution", "data": {"message": "Blueprint ready", "phase": "blueprint"}}],
        True,
        "send emails",
        goal="send emails on Diwali",
    )
    assert out["blocked_normal_reply"] is True
    assert out.get("summary")
    assert out.get("ui_events")


def test_youtube_blueprint_requires_api_key(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "YouTube cred gate", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build workflow to sync YouTube channel stats daily",
        )
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        assert sol.get("phase") == "blueprint"
        assert "youtube_api_key" in (sol.get("missing_credentials") or [])
        assert "Approve" not in (sol.get("chips") or [])

        blocked = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="approve",
        )
        assert any(e["type"] == "aios_credentials_needed" for e in blocked["events"])
        assert not any(
            e["type"] == "aios_approved" for e in blocked["events"]
        )
    finally:
        db.close()


def test_youtube_goal_uses_youtube_not_email_template(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "YouTube template", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build workflow to sync YouTube channel stats daily",
        )
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        preview = sol.get("executable_preview") or {}
        nodes = preview.get("nodes") or []
        node_ids = [n.get("id") for n in nodes]
        assert any(nid == "youtube" for nid in node_ids)
        assert not any(str(nid).startswith("email_") for nid in node_ids)
        steps = (sol.get("blueprint") or {}).get("steps") or []
        joined = " ".join(steps).lower()
        assert "youtube" in joined
        assert "email digest" not in joined
        assert sol.get("requirements", {}).get("integration") == "youtube"
        assert "YouTube" in (sol.get("friendly_title") or "")
    finally:
        db.close()


def test_email_goal_still_builds_multi_email_workflow(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Email template", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Create a workflow to send 5 emails on different subjects to my friends about Diwali",
        )
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        preview = sol.get("executable_preview") or {}
        node_ids = [n.get("id") for n in (preview.get("nodes") or [])]
        assert any(str(nid).startswith("email_") for nid in node_ids)
        steps = (sol.get("blueprint") or {}).get("steps") or []
        assert "email" in " ".join(steps).lower()
    finally:
        db.close()


def test_youtube_paste_saves_vault_and_allows_approve(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import CredentialVaultEntry, SessionLocal
    from app.services import credential_vault as vault

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "YouTube paste", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        db.query(CredentialVaultEntry).filter(
            CredentialVaultEntry.workspace_id == 1,
            CredentialVaultEntry.category == "youtube",
        ).delete(synchronize_session=False)
        db.commit()

        process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build workflow to post YouTube stats",
        )
        paste = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="youtube api key is AIzaSyBvOkBwvOkBwvOkBwvOkBwvOkBwvOkB",
        )
        assert any(e["type"] == "aios_credentials_saved" for e in paste["events"])
        rows = vault.list_entries(db, 1, category="youtube")
        assert len(rows) >= 1

        approve = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="approve",
        )
        assert "aios_approved" in [e["type"] for e in approve["events"]]
    finally:
        db.close()


def test_google_sheets_goal_missing_oauth_labels(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Google sheets", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Automate updates to my Google Sheets excel report",
        )
        sol = next(e for e in compose["events"] if e["type"] == "aios_solution")["data"]
        missing = sol.get("missing_credentials") or []
        assert any("google" in m for m in missing)
    finally:
        db.close()
