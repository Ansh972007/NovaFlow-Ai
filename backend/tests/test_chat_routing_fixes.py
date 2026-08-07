"""Tests for chat routing: Q&A vs workflows, credentials, approve async safety."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.orm import Session

from app.composer.chat_advanced import is_conversational_message, is_refine_message
from app.composer.chat_router import is_qa_message, universal_route
from app.composer.planner import infer_capabilities_from_goal
from app.composer.chat_requirements import parse_requirements, gather_prompt, missing_workflow_slots
from app.database import SessionLocal, init_db
from app.sandbox.credential_probes import check_credential_probe
from app.sandbox.enterprise_suite import run_enterprise_suite


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_hello_is_conversational():
    assert is_conversational_message("hello")
    assert not is_refine_message("hello")


def test_what_is_gmail_routes_qa_not_work():
    route = universal_route("what is Gmail?", has_pending=False)
    assert route["route"] == "qa"
    assert route["intent_hint"] == "chat"
    assert is_qa_message("what is Gmail?")


def test_calendar_meetings_goal_infers_google_cap():
    caps = infer_capabilities_from_goal(
        "my calendar holds my meeting dates can you make it",
        force_workflow=True,
    )
    assert "cap_google" in caps
    req = parse_requirements("my calendar holds my meeting dates")
    assert req.get("integration") == "google_calendar"
    slots = missing_workflow_slots(req)
    assert any(s["id"] == "auth_preference" for s in slots)


def test_gather_prompt_not_ready_without_creds():
    req = parse_requirements("telegram bot for alerts")
    msg = gather_prompt(req, [], ["telegram_bot_token"])
    assert "Everything looks ready" not in msg
    assert "Credentials needed" in msg or "credentials" in msg.lower()


def test_credential_probe_from_running_loop(db: Session):
    graph = {
        "nodes": [
            {"id": "t", "type": "trigger"},
            {"id": "n", "type": "notify", "data": {"channel": "telegram"}},
        ],
        "edges": [],
    }

    async def _inner():
        from app.database import Workspace

        ws = db.query(Workspace).first()
        if not ws:
            pytest.skip("no workspace")
        result = check_credential_probe(db, ws.id, graph, missing_credentials=None)
        assert result.get("id") == "credential_probe"

    asyncio.run(_inner())


def test_enterprise_suite_inside_asyncio_run(db: Session):
    from app.database import Workspace

    ws = db.query(Workspace).first()
    if not ws:
        pytest.skip("no workspace")
    graph = {
        "nodes": [
            {"id": "trigger", "type": "trigger"},
            {"id": "llm", "type": "llm", "data": {"prompt": "hi"}},
            {"id": "output", "type": "output"},
        ],
        "edges": [{"from": "trigger", "to": "llm"}, {"from": "llm", "to": "output"}],
    }

    async def _runner():
        report = run_enterprise_suite(
            graph,
            db=db,
            workspace_id=ws.id,
            live_credential_probe=True,
        )
        assert report.get("suite") == "enterprise"

    asyncio.run(_runner())


def test_make_it_not_approve_during_gather_message():
    """make it during gather should not produce ready-to-approve copy."""
    req = parse_requirements("telegram bot")
    slots = missing_workflow_slots(req)
    msg = gather_prompt(req, slots, ["telegram_bot_token"])
    assert "Everything looks ready" not in msg


def test_hello_with_pending_blueprint_clears_compose(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "routing hello", "conversation_type": "assistant"},
    ).json()["data"]
    conv_id = conv["id"]

    db = SessionLocal()
    try:
        compose = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="express compose build a telegram support bot that answers from knowledge",
        )
        assert any(e["type"] == "aios_solution" for e in compose["events"])

        hello = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv_id,
            user_message="hello",
        )
        assert not any(e["type"] == "aios_solution" for e in hello.get("events") or [])
        assert hello.get("blocked_normal_reply") is False
    finally:
        db.close()


def _auth_headers(api_client):
    from tests.test_smoke import _auth_headers as _h

    return _h(api_client)
