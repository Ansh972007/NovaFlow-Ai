"""End-to-end execution tests for every builtin workflow node type."""

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.database import KnowledgeBase, NodeDefinition, SessionLocal, User, Workflow
from app.services.tenancy import ensure_personal_workspace
from app.workflow_intelligence.node_registry import get_known_node_types, merge_node_data_with_defaults


def _chain_graph(node_type: str, node_data: dict | None = None) -> dict:
    mid_data = merge_node_data_with_defaults(node_type, node_data or {})
    return {
        "nodes": [
            {"id": "trigger", "type": "trigger", "data": merge_node_data_with_defaults("trigger", {})},
            {"id": "mid", "type": node_type, "data": mid_data},
            {"id": "output", "type": "output", "data": merge_node_data_with_defaults("output", {})},
        ],
        "edges": [
            {"from": "trigger", "to": "mid"},
            {"from": "mid", "to": "output"},
        ],
    }


async def _execute(db, graph: dict, user_input: str, workspace_id: int, user_id: int):
    from app.services.workflow import _execute_graph

    return await _execute_graph(
        db,
        user_id,
        graph,
        user_input,
        workspace_id=workspace_id,
    )


@pytest.fixture
def ws_ctx():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        pytest.skip("no user")
    ws = ensure_personal_workspace(db, user)
    yield db, user.user_id, ws.id
    db.close()


LLM_PATCH = patch(
    "app.workflow_intelligence.execution.runtime_bridge.workflow_llm_sync",
    new_callable=AsyncMock,
    return_value="Mock LLM reply for workflow test.",
)
RETRIEVE_PATCH = patch(
    "app.workflow_intelligence.execution.runtime_bridge.workflow_retrieve",
    new_callable=AsyncMock,
    return_value=("Retrieved context chunk one.", 2),
)
AGENT_PATCH = patch(
    "app.workflow_intelligence.execution.runtime_bridge.workflow_agent",
    new_callable=AsyncMock,
    return_value={"output": "Agent summary: all checks passed."},
)
NOTIFY_PATCH = patch(
    "app.services.workflow.send_notification",
    new_callable=AsyncMock,
    return_value={"ok": True, "detail": "Notification sent (test)"},
)
HTTP_PATCH = patch(
    "app.services.workflow._fetch_http",
    new_callable=AsyncMock,
    return_value='{"ok": true, "source": "mock_http"}',
)
JIRA_PATCH = patch(
    "app.services.gmail_jira.jira_create_issue",
    new_callable=AsyncMock,
    return_value={"key": "NF-101", "id": "10001"},
)
GITHUB_PATCH = patch(
    "app.services.github_issues.github_create_issue",
    new_callable=AsyncMock,
    return_value={"number": 42, "html_url": "https://github.com/org/repo/issues/42"},
)
LINEAR_PATCH = patch(
    "app.services.linear_issues.linear_create_issue",
    new_callable=AsyncMock,
    return_value={"identifier": "ENG-99", "id": "lin-1", "url": "https://linear.app/issue/ENG-99"},
)
API_NODE_PATCH = patch(
    "app.services.api_node_runtime.execute_api_node_definition",
    new_callable=AsyncMock,
    return_value=('{"api": "ok"}', {"status_code": 200}),
)
COMPONENT_PATCH = patch(
    "app.services.dynamic_component_runtime.execute_dynamic_component",
    new_callable=AsyncMock,
    return_value={"output": "Component output OK"},
)


def _assert_mid_ok(steps: list, node_type: str):
    mid = next(s for s in steps if s.get("node_id") == "mid")
    assert mid.get("status") == "ok", f"{node_type} failed: {mid.get('output')}"


def _assert_run_ok(node_type: str, context: dict, steps: list):
    _assert_mid_ok(steps, node_type)
    if node_type == "retrieve":
        assert context.get("retrieved"), "retrieve should populate retrieved context"
    elif node_type == "trigger":
        assert context.get("input"), "trigger should preserve input"
    else:
        assert context.get("output"), f"{node_type} produced empty output"


@pytest.mark.parametrize("node_type", sorted(get_known_node_types()))
def test_builtin_node_executes(node_type: str, ws_ctx):
    db, user_id, workspace_id = ws_ctx

    if node_type in ("api_node", "component_node"):
        pytest.skip("covered by dedicated fixture tests")

    graph = _chain_graph(node_type)
    user_input = "hello world test"

    if node_type == "retrieve":
        kb = KnowledgeBase(name="Test KB", user_id=user_id, workspace_id=workspace_id)
        db.add(kb)
        db.commit()
        db.refresh(kb)
        graph = _chain_graph("retrieve", {"knowledge_id": kb.id, "query": "{{input}}", "limit": 3})

    if node_type == "condition":
        graph = _chain_graph("condition", {"keyword": "hello", "then_text": "matched", "else_text": "no match"})
        user_input = "hello there"

    if node_type == "transform":
        graph = _chain_graph("transform", {"template": "PREFIX: {{input}}"})

    if node_type == "notify":
        graph = _chain_graph(
            "notify",
            {
                "channel": "email",
                "from": "sender@test.local",
                "to": "recipient@test.local",
                "subject": "Test subject",
                "message": "Body {{output}}",
            },
        )

    if node_type == "human":
        graph = _chain_graph("human", {"require_approval": False, "message": "Review {{input}}"})

    if node_type == "loop":
        graph = _chain_graph("loop", {"max": 2, "separator": "|", "merge": False})
        user_input = "alpha|beta"

    if node_type == "parallel":
        graph = _chain_graph("parallel", {"branches": ["Summary", "Risks"]})

    if node_type == "agent":
        graph = _chain_graph("agent", {"tools": ["summarize"]})

    if node_type == "jira":
        graph = _chain_graph("jira", {"action": "create", "project_key": "NF", "summary": "Test", "description": "Desc"})

    if node_type == "github":
        graph = _chain_graph("github", {"action": "create", "title": "Bug", "body": "Details", "labels": "bug"})

    if node_type == "linear":
        graph = _chain_graph("linear", {"action": "create", "title": "Task", "description": "Do work"})

    if node_type == "http":
        graph = _chain_graph(
            "http",
            {
                "url": "https://api.example.com/ping",
                "method": "GET",
                "auth": "custom",
                "set_output": True,
            },
        )

    if node_type == "subgraph":
        child = Workflow(
            name="child wf",
            desc="",
            graph_json=json.dumps(
                {
                    "nodes": [
                        {"id": "t", "type": "trigger", "data": {}},
                        {"id": "o", "type": "output", "data": {}},
                    ],
                    "edges": [{"from": "t", "to": "o"}],
                }
            ),
            user_id=user_id,
            workspace_id=workspace_id,
            status=1,
        )
        db.add(child)
        db.commit()
        db.refresh(child)
        graph = _chain_graph("subgraph", {"workflow_id": child.id, "label": "Child"})

    with LLM_PATCH, RETRIEVE_PATCH, AGENT_PATCH, NOTIFY_PATCH, HTTP_PATCH, JIRA_PATCH, GITHUB_PATCH, LINEAR_PATCH:
        context, steps, pause = asyncio.run(_execute(db, graph, user_input, workspace_id, user_id))

    assert pause is None, f"{node_type} unexpectedly paused for human review"
    _assert_run_ok(node_type, context, steps)


def test_api_node_executes(ws_ctx):
    db, user_id, workspace_id = ws_ctx
    definition = {
        "http": {"url": "https://api.example.com/v1/test", "method": "GET", "auth": "custom"},
        "input_schema": {"fields": [{"key": "q", "label": "Query", "type": "text", "default": "x"}]},
    }
    row = NodeDefinition(
        workspace_id=workspace_id,
        created_by=user_id,
        slug="test-api-node",
        display_name="Test API Node",
        definition_json=json.dumps(definition),
        status="published",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    graph = _chain_graph("api_node", {"node_def_id": row.id, "label": "API", "q": "search", "set_output": True})

    with API_NODE_PATCH, LLM_PATCH, RETRIEVE_PATCH:
        context, steps, pause = asyncio.run(_execute(db, graph, "hello", workspace_id, user_id))

    assert pause is None
    _assert_mid_ok(steps, "api_node")
    assert "api" in (context.get("output") or "")


def test_component_node_executes(ws_ctx):
    db, user_id, workspace_id = ws_ctx
    graph = _chain_graph(
        "component_node",
        {"component_name": "test_component", "set_output": True, "input_text": "{{input}}"},
    )

    with COMPONENT_PATCH, LLM_PATCH, RETRIEVE_PATCH:
        context, steps, pause = asyncio.run(_execute(db, graph, "component input", workspace_id, user_id))

    assert pause is None
    _assert_mid_ok(steps, "component_node")
    assert "Component" in (context.get("output") or "")


def test_human_pause_when_approval_required(ws_ctx):
    db, user_id, workspace_id = ws_ctx
    graph = _chain_graph("human", {"require_approval": True, "message": "Approve {{input}}"})

    with LLM_PATCH, RETRIEVE_PATCH:
        context, steps, pause = asyncio.run(_execute(db, graph, "review me", workspace_id, user_id))

    assert pause == "mid"
    mid = next(s for s in steps if s.get("node_id") == "mid")
    assert mid.get("status") == "pending_human"


def test_notify_channels_execute(ws_ctx):
    """Email, telegram, slack, discord, webhook notify paths."""
    db, user_id, workspace_id = ws_ctx
    channels = [
        ("email", {"channel": "email", "to": "a@b.com", "subject": "S", "message": "M"}),
        ("telegram", {"channel": "telegram", "to": "12345", "message": "Hi"}),
        ("slack", {"channel": "slack", "to": "https://hooks.slack.com/test", "message": "Hi"}),
        ("discord", {"channel": "discord", "to": "https://discord.com/api/webhooks/test", "message": "Hi"}),
        ("webhook", {"channel": "webhook", "to": "https://hooks.example.com/n", "message": "Hi"}),
    ]
    with NOTIFY_PATCH, LLM_PATCH, RETRIEVE_PATCH:
        for ch_name, data in channels:
            graph = _chain_graph("notify", data)
            context, steps, pause = asyncio.run(_execute(db, graph, "notify test", workspace_id, user_id))
            assert pause is None, ch_name
            _assert_mid_ok(steps, f"notify-{ch_name}")


def test_http_methods_execute(ws_ctx):
    db, user_id, workspace_id = ws_ctx
    methods = ["GET", "POST", "PUT", "DELETE"]
    with HTTP_PATCH, LLM_PATCH, RETRIEVE_PATCH:
        for method in methods:
            graph = _chain_graph(
                "http",
                {
                    "url": "https://api.example.com/resource",
                    "method": method,
                    "body": '{"id": 1}' if method in ("POST", "PUT") else "",
                    "set_output": True,
                },
            )
            context, steps, pause = asyncio.run(_execute(db, graph, "http test", workspace_id, user_id))
            assert pause is None, method
            _assert_mid_ok(steps, f"http-{method}")
