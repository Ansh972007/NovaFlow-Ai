"""Async process_chat_turn approve path — no event loop nesting errors."""

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy.orm import Session

from app.database import Conversation, SessionLocal, init_db


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_process_chat_turn_approve_from_async_context(db: Session):
    from app.composer.chat_bridge import process_chat_turn

    conv = Conversation(
        title="approve async",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json=json.dumps(
            {
                "aios": {
                    "compose_phase": "await_approve",
                    "phase": "blueprint",
                    "status": "blueprint",
                    "goal": "telegram bot for alerts",
                    "requirements": parse_requirements_stub(),
                    "executable_preview": minimal_graph(),
                    "required_capabilities": ["cap_workflow", "cap_telegram"],
                    "friendly_title": "Telegram Bot Workflow",
                }
            }
        ),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    async def _run():
        return await process_chat_turn(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv.id,
            user_message="Approve",
            workspace_role="editor",
        )

    result = asyncio.run(_run())
    assert "events" in result or result.get("blocked_normal_reply") is not None
    # Must not raise "Cannot run the event loop while another loop is running"
    err_events = [
        e for e in (result.get("events") or [])
        if e.get("type") == "aios_error"
        and "event loop" in str((e.get("data") or {}).get("message", "")).lower()
    ]
    assert not err_events


def parse_requirements_stub():
    from app.composer.chat_requirements import parse_requirements

    return parse_requirements("telegram bot for alerts")


def minimal_graph():
    return {
        "nodes": [
            {"id": "trigger", "type": "trigger", "data": {"label": "Start"}},
            {"id": "llm", "type": "llm", "data": {"prompt": "hi"}},
            {"id": "output", "type": "output", "data": {"label": "Output"}},
        ],
        "edges": [
            {"from": "trigger", "to": "llm"},
            {"from": "llm", "to": "output"},
        ],
    }


def test_run_sync_from_async_nested_in_asyncio(db: Session):
    from app.composer.chat_bridge import process_chat_goal
    from app.runtime.async_bridge import run_sync_from_async

    async def inner():
        return run_sync_from_async(
            process_chat_goal,
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=None,
            user_message="what can you do?",
        )

    out = asyncio.run(inner())
    assert out is not None
