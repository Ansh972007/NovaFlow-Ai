"""Regression tests for production chat transcript scenarios."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from app.composer.chat_actions import classify_ops_intent, requirements_confirm_action
from app.composer.chat_bridge import _clear_pending_blueprint, classify_intent, process_chat_goal
from app.composer.chat_channels import filter_real_credential_items, extract_channel_credentials
from app.composer.chat_requirements import build_requirements_brief, parse_requirements
from app.database import Conversation, SessionLocal, init_db


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_run_it_classifies_as_run_workflow_not_approve():
    assert classify_ops_intent("run it") == "run_workflow"
    assert classify_ops_intent("now run it") == "run_workflow"
    assert classify_ops_intent("test workflow") == "test_workflow"
    assert classify_ops_intent("run workflow 1 and 3") == "run_workflows_parallel"
    assert classify_intent("run it", has_pending=True) == "run_workflow"


def test_show_workflow_and_count_ops():
    assert classify_ops_intent("show me my workflow") == "list_workflows"
    assert classify_ops_intent("how many workflows") == "list_workflows"


def test_store_in_knowledge_ops():
    assert classify_ops_intent("store this in knowledge") == "store_chat_knowledge"
    assert classify_ops_intent("save to knowledge") == "store_chat_knowledge"
    assert classify_ops_intent("how many workflows do we have total") == "list_workflows"
    assert classify_ops_intent("store this data in knowlage") == "store_chat_knowledge"


def test_hybrid_youtube_question_not_blocked_for_ops():
    from app.composer.chat_bridge import process_chat_goal
    from app.database import Conversation, SessionLocal

    db = SessionLocal()
    conv = Conversation(
        title="ops hybrid",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json="{}",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    out = process_chat_goal(
        db,
        workspace_id=1,
        user_id=1,
        conversation_id=conv.id,
        user_message="how many workflows do we have total",
    )
    assert out.get("needs_ops_dispatch") or out.get("ops_intent") == "list_workflows"
    db.close()


def test_placeholder_credentials_rejected():
    items = extract_channel_credentials("my email is you@gmail.com password is xxxx")
    ok, rejected = filter_real_credential_items(items)
    assert not ok
    assert rejected


def test_real_email_not_rejected_as_placeholder():
    items = extract_channel_credentials("my email is alice.real@company.io password is abcdabcdabcdabcd")
    ok, rejected = filter_real_credential_items(items)
    assert ok
    assert not rejected


def test_clear_pending_blueprint_wipes_stale_goal():
    aios = {
        "goal": "send emails",
        "requirements": {"integration": "gmail"},
        "requirements_confirmed": True,
        "compose_phase": "blueprint",
        "solution_id": "sol-1",
        "memory_hints": ["recipe:email", "field:support"],
    }
    cleared = _clear_pending_blueprint(aios)
    assert cleared.get("goal") is None
    assert cleared.get("requirements") is None
    assert cleared.get("requirements_confirmed") is None
    assert cleared.get("solution_id") is None
    assert cleared.get("memory_hints") == []


def test_build_requirements_brief_shape():
    req = parse_requirements("build a telegram bot for alerts")
    brief = build_requirements_brief(req, {"planning_label": "Test · gpt-4o-mini", "source": "workspace"})
    assert brief["type"] == "aios_requirements_brief"
    assert brief["data"]["planning_label"] == "Test · gpt-4o-mini"
    assert "Yes build this" in brief["data"]["chips"]


def test_requirements_confirm_sets_flag_and_recompose(db: Session):
    conv = Conversation(
        title="test",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json=json.dumps(
            {
                "aios": {
                    "pending_compose_goal": "build email digest workflow",
                    "requirements_confirmed": False,
                }
            }
        ),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    result = requirements_confirm_action(db, conversation_id=conv.id)
    assert result.get("recompose_after_confirm")
    assert result.get("recompose_goal") == "build email digest workflow"

    db.refresh(conv)
    meta = json.loads(conv.meta_json or "{}")
    assert meta["aios"]["requirements_confirmed"] is True


def test_compose_shows_brief_before_blueprint(db: Session):
    conv = Conversation(
        title="compose test",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json="{}",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    bridge = process_chat_goal(
        db,
        workspace_id=1,
        user_id=1,
        conversation_id=conv.id,
        user_message="build a workflow for my team",
    )
    events = bridge.get("events") or []
    types = [e.get("type") for e in events]
    assert "aios_requirements_brief" in types
    assert bridge.get("blocked_normal_reply")


def test_resolve_chat_llm_config_workspace_fallback(db: Session):
    from app.composer.llm_resolve import resolve_chat_llm_config

    cfg = resolve_chat_llm_config(db, workspace_id=1, user_id=1, aios={})
    assert cfg.get("source") in ("workspace", "vault", "user", "conversation", "override", "none")
    assert "planning_label" in cfg
    assert "available_alternatives" in cfg
