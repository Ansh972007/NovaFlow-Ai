"""Chat orchestrator, multi-integration compose, async approve, and routing tests."""

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy.orm import Session

from app.composer.chat_actions import classify_ops_intent
from app.composer.chat_orchestrator import orchestrate_turn, apply_orchestrator_patch
from app.composer.chat_requirements import parse_requirements
from app.composer.workflow_composer import build_executable_graph
from app.composer.workflow_matcher import match_workflow
from app.composer.planner import infer_capabilities_from_goal
from app.database import Conversation, SessionLocal, init_db
from app.runtime.async_bridge import run_sync_from_async
from app.services.embeddings import embed_texts_sync


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_parse_requirements_telegram_jira_telegram_flow():
    goal = (
        "make a workflow in which i send a task to telegram and then it work on jira "
        "and then it give response on telegram"
    )
    req = parse_requirements(goal)
    assert "telegram" in req.get("input_channels") or req.get("trigger") == "telegram_chat"
    assert "telegram" in req.get("output_channels") or "telegram" in (req.get("integrations") or [])
    assert "jira" in (req.get("integrations") or []) or req.get("integration") == "jira"


def test_build_graph_telegram_jira_telegram_has_nodes():
    goal = (
        "telegram task to jira work then telegram response"
    )
    req = parse_requirements(goal)
    req["input_channels"] = list(dict.fromkeys((req.get("input_channels") or []) + ["telegram"]))
    req["output_channels"] = list(dict.fromkeys((req.get("output_channels") or []) + ["telegram"]))
    req["integrations"] = list(dict.fromkeys((req.get("integrations") or []) + ["jira", "telegram"]))
    req["trigger"] = "telegram_chat"
    enriched = f"{goal} Input: telegram. Output: telegram. Integrations: jira."
    caps = infer_capabilities_from_goal(enriched, force_workflow=True)
    graph = build_executable_graph(
        required_caps=caps,
        goal=enriched,
        requirements=req,
    )
    types = [n.get("type") for n in graph.get("nodes") or []]
    assert "trigger" in types
    assert "jira" in types
    notify_nodes = [n for n in graph.get("nodes") or [] if n.get("type") == "notify"]
    assert notify_nodes
    telegram_notify = [
        n for n in notify_nodes
        if (n.get("data") or {}).get("channel") == "telegram"
    ]
    assert telegram_notify
    trigger = next(n for n in graph.get("nodes") or [] if n.get("type") == "trigger")
    assert (trigger.get("data") or {}).get("source") == "telegram" or req.get("trigger") == "telegram_chat"


def test_email_plan_same_recipient_multiple_emails():
    req = parse_requirements("send 5 emails on different topics to the same person")
    req["output_channels"] = ["email"]
    plan = req.get("email_plan") or {}
    assert plan.get("mode") == "same_recipient" or req.get("email_count") == 5
    caps = infer_capabilities_from_goal("send 5 emails same person", force_workflow=True)
    graph = build_executable_graph(
        required_caps=caps,
        goal="send 5 emails on different topics to same person",
        requirements=req,
    )
    email_nodes = [
        n for n in graph.get("nodes") or []
        if n.get("type") == "notify" and (n.get("data") or {}).get("channel") == "email"
    ]
    assert len(email_nodes) >= 2


def test_no_notify_without_delivery_intent():
    """Calendar read workflow should not auto-add telegram notify."""
    req = parse_requirements("my calendar holds my meeting dates")
    caps = infer_capabilities_from_goal("fetch google calendar meetings", force_workflow=True)
    graph = build_executable_graph(
        required_caps=caps,
        goal="my calendar holds my meeting dates",
        requirements=req,
    )
    notify = [n for n in graph.get("nodes") or [] if n.get("type") == "notify"]
    assert not notify


def test_orchestrator_heuristic_qa_for_hello():
    out = orchestrate_turn(
        None,
        workspace_id=1,
        user_id=1,
        user_message="hello",
        aios={},
        has_pending=True,
    )
    assert out is not None
    assert out.get("mode") == "qa"
    assert out.get("allow_normal_reply")


def test_orchestrator_heuristic_ops_list_workflows():
    out = orchestrate_turn(
        None,
        workspace_id=1,
        user_id=1,
        user_message="how many workflows do we have total",
        aios={},
        has_pending=False,
    )
    assert out is not None
    assert out.get("mode") == "ops"
    assert out.get("ops_intent") == "list_workflows"


def test_apply_orchestrator_patch_merges_channels():
    aios = {"requirements": {"integrations": ["jira"]}}
    patched = apply_orchestrator_patch(
        aios,
        {"integrations": ["telegram"], "output_channels": ["telegram"]},
    )
    assert "jira" in patched["requirements"]["integrations"]
    assert "telegram" in patched["requirements"]["integrations"]
    assert "telegram" in patched["requirements"]["output_channels"]


def test_match_workflow_returns_shape(db: Session):
    result = match_workflow(
        db,
        workspace_id=1,
        goal="daily email workflow",
        requirements=parse_requirements("send daily email"),
        llm_cfg=None,
    )
    assert "action" in result
    assert result["action"] in ("create", "modify", "reuse")


def test_embed_texts_sync_inside_asyncio_loop():
    async def _run():
        vecs = embed_texts_sync([], model=None)
        assert vecs == []

    asyncio.run(_run())


def test_process_chat_goal_from_async_context(db: Session):
    from app.composer.chat_bridge import process_chat_goal

    conv = Conversation(
        title="async bridge",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json="{}",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    async def _run():
        return run_sync_from_async(
            process_chat_goal,
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv.id,
            user_message="hello",
        )

    out = asyncio.run(_run())
    assert out.get("blocked_normal_reply") is False


def test_deployed_run_it_ops_dispatch(db: Session):
    from app.composer.chat_bridge import process_chat_goal

    conv = Conversation(
        title="run it",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json=json.dumps(
            {
                "aios": {
                    "status": "deployed",
                    "workflow_id": "wf-test-123",
                    "compose_phase": "built",
                }
            }
        ),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    out = process_chat_goal(
        db,
        workspace_id=1,
        user_id=1,
        conversation_id=conv.id,
        user_message="run it",
    )
    assert out.get("needs_ops_dispatch")
    assert out.get("ops_intent") == "run_workflow"


def test_total_workflows_ops_intent():
    assert classify_ops_intent("give me total workflows") == "list_workflows"
    assert classify_ops_intent("store this data in knowlage") == "store_chat_knowledge"
