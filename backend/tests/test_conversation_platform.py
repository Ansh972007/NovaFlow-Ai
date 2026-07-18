"""Enterprise Conversation Platform tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.conversation.export import export_conversation
from app.conversation.integration import persist_chat_turn
from app.conversation.search import search_conversations
from app.conversation.service import append_message, create_conversation, get_conversation, get_messages
from app.conversation.threading import fork_conversation, pin_conversation
from app.database import SessionLocal, User, init_db


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_id(db: Session) -> int:
    u = db.query(User).first()
    assert u
    return u.user_id


def test_create_conversation_and_messages(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id, title="Test chat", resource_id="asst1")
    assert c.id
    append_message(db, c, content="Hello", message_type="user", role="user", created_by=user_id)
    append_message(db, c, content="Hi there", message_type="assistant", role="assistant", created_by=user_id)
    msgs = get_messages(db, c.id, workspace_id=1)
    assert len(msgs) == 2


def test_tenant_isolation(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id)
    assert get_conversation(db, c.id, workspace_id=99999) is None


def test_search(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id, title="Invoice processing help")
    append_message(db, c, content="How do I process invoices?", message_type="user", role="user")
    result = search_conversations(db, workspace_id=1, query="invoice")
    assert result["total_conversations"] >= 1 or result["total_messages"] >= 1


def test_fork(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id)
    m = append_message(db, c, content="Branch point", message_type="user", role="user")
    fork = fork_conversation(db, c, parent_message_id=m.id, user_id=user_id)
    assert fork.get("conversation_id")


def test_export_markdown(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id, title="Export test")
    append_message(db, c, content="Question", message_type="user", role="user")
    out = export_conversation(db, c.id, workspace_id=1, fmt="markdown")
    assert "Export test" in out["content"]
    json_out = export_conversation(db, c.id, workspace_id=1, fmt="json")
    assert "messages" in json_out["content"]


def test_persist_chat_turn(db: Session, user_id: int):
    meta = persist_chat_turn(
        db,
        workspace_id=1,
        user_id=user_id,
        organization_id=None,
        assistant_id="aid123",
        user_message="What is NovaFlow?",
        assistant_message="NovaFlow is an AI platform.",
        trace_id="trace123",
    )
    assert meta.get("conversation_id")
    c = get_conversation(db, meta["conversation_id"], workspace_id=1)
    assert c is not None


def test_pin(db: Session, user_id: int):
    c = create_conversation(db, workspace_id=1, user_id=user_id)
    pin_conversation(db, c, True)
    db.refresh(c)
    assert c.pinned == 1
