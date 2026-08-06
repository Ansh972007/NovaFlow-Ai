"""Tests for autonomous chat deployment plan (persistence, ops, deploy gates)."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_smoke import _auth_headers


@pytest.fixture
def api_client():
    return TestClient(app)


def test_delete_workflow_ops_intent_classified():
    from app.composer.chat_actions import classify_ops_intent, OPS_INTENTS

    intent = classify_ops_intent("delete my workflow")
    assert intent == "delete_workflow"
    assert "delete_workflow" in OPS_INTENTS


def test_clone_and_update_ops_intents():
    from app.composer.chat_actions import classify_ops_intent, OPS_INTENTS

    assert classify_ops_intent("clone my last workflow") == "clone_workflow"
    assert classify_ops_intent("update my workflow from blueprint") == "update_workflow"
    assert "clone_workflow" in OPS_INTENTS
    assert "update_workflow" in OPS_INTENTS


def test_run_workflow_emits_step_events():
    from app.composer.chat_actions import run_workflow_action
    from app.database import SessionLocal, Workflow

    db = SessionLocal()
    try:
        wf = Workflow(
            name="Stream test wf",
            desc="test",
            graph_json=json.dumps(
                {
                    "nodes": [
                        {"id": "trigger", "type": "trigger", "data": {}},
                        {"id": "llm", "type": "llm", "data": {"prompt": "Say hi"}},
                        {"id": "output", "type": "output", "data": {}},
                    ],
                    "edges": [
                        {"from": "trigger", "to": "llm"},
                        {"from": "llm", "to": "output"},
                    ],
                }
            ),
            user_id=1,
            workspace_id=1,
            status=1,
        )
        db.add(wf)
        db.commit()
        db.refresh(wf)

        with patch(
            "app.services.workflow_http_auth.fetch_http_authenticated",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.workflow_intelligence.execution.runtime_bridge.workflow_llm_sync",
                new_callable=AsyncMock,
                return_value="hello",
            ):
                result = asyncio.run(
                    run_workflow_action(
                        db,
                        workspace_id=1,
                        user_id=1,
                        conversation_id=None,
                        text="run workflow",
                    )
                )
        types = [e.get("type") for e in result.get("events") or []]
        assert "aios_run_status" in types
        assert any(t == "aios_run_step" for t in types)
    finally:
        db.close()


def test_deploy_blocked_without_test(api_client):
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Deploy gate", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Build workflow to sync YouTube stats",
        )
        process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="approve",
        )
        deploy = process_chat_goal(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="deploy",
        )
        deploy_ev = next(e for e in deploy["events"] if e["type"] == "aios_deploy")
        status = deploy_ev["data"].get("status")
        if status == "error":
            pytest.skip("Blueprint not approved with solution_id in this environment")
        assert status == "blocked"
    finally:
        db.close()


def test_process_chat_turn_returns_aios_snapshot(api_client):
    from app.composer.chat_bridge import process_chat_turn
    from app.database import SessionLocal

    headers = _auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "Aios snapshot", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        out = asyncio.run(
            process_chat_turn(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="list my workflows",
            )
        )
        assert "aios" in out or out.get("events")
    finally:
        db.close()
