"""AgentOS registry — types, templates, capabilities."""

from __future__ import annotations

from typing import Any

AGENT_TYPES: dict[str, dict[str, Any]] = {
    "research": {
        "description": "Research and gather evidence",
        "default_tools": ["kb_search", "web_fetch", "summarize"],
        "roles": ["research", "reviewer", "writer"],
    },
    "knowledge": {
        "description": "Knowledge retrieval and citation",
        "default_tools": ["kb_search", "summarize"],
        "roles": ["research", "writer"],
    },
    "coding": {
        "description": "Code generation and analysis",
        "default_tools": ["summarize", "json_parse", "regex_extract"],
        "roles": ["developer", "reviewer", "writer"],
    },
    "workflow": {
        "description": "Workflow automation agent",
        "default_tools": ["summarize", "datetime"],
        "roles": ["planner", "coordinator"],
    },
    "evaluation": {
        "description": "Evaluation and QA agent",
        "default_tools": ["kb_search", "summarize"],
        "roles": ["reviewer", "writer"],
    },
    "monitoring": {
        "description": "Monitoring and alerting agent",
        "default_tools": ["datetime", "summarize"],
        "roles": ["research", "writer"],
    },
    "supervisor": {
        "description": "Supervisor orchestrating sub-agents",
        "default_tools": ["summarize"],
        "roles": ["planner", "coordinator"],
    },
    "custom": {
        "description": "Custom enterprise agent",
        "default_tools": ["summarize"],
        "roles": ["writer"],
    },
}

AGENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "research_pipeline": {
        "agent_type": "research",
        "name": "Research Pipeline",
        "roles": ["research", "reviewer", "writer", "coordinator"],
        "tools": ["kb_search", "web_fetch", "summarize"],
    },
    "code_review": {
        "agent_type": "coding",
        "name": "Code Review Agent",
        "roles": ["developer", "reviewer", "writer"],
        "tools": ["summarize", "json_parse"],
    },
    "knowledge_qa": {
        "agent_type": "knowledge",
        "name": "Knowledge Q&A",
        "roles": ["research", "writer"],
        "tools": ["kb_search", "summarize"],
    },
    "deep_research": {
        "agent_type": "research",
        "name": "Deep Research Agent",
        "roles": ["research", "reviewer", "writer", "coordinator"],
        "tools": ["kb_search", "web_fetch", "summarize"],
    },
    "coding_assistant": {
        "agent_type": "coding",
        "name": "Coding Agent",
        "roles": ["developer", "reviewer", "writer"],
        "tools": ["summarize", "json_parse", "regex_extract"],
    },
    "legal_assistant": {
        "agent_type": "custom",
        "name": "Legal Agent",
        "roles": ["reviewer", "writer"],
        "tools": ["kb_search", "summarize"],
    },
    "finance_assistant": {
        "agent_type": "custom",
        "name": "Finance Agent",
        "roles": ["research", "writer"],
        "tools": ["kb_search", "summarize"],
    },
    "hr_assistant": {
        "agent_type": "custom",
        "name": "HR Agent",
        "roles": ["writer"],
        "tools": ["kb_search", "summarize"],
    },
    "marketing_assistant": {
        "agent_type": "custom",
        "name": "Marketing Agent",
        "roles": ["writer"],
        "tools": ["kb_search", "summarize"],
    },
    "support_assistant": {
        "agent_type": "custom",
        "name": "Support Agent",
        "roles": ["research", "writer"],
        "tools": ["kb_search", "summarize"],
    },
    "database_assistant": {
        "agent_type": "custom",
        "name": "Database Agent",
        "roles": ["developer", "writer"],
        "tools": ["json_parse", "summarize"],
    },
    "security_assistant": {
        "agent_type": "evaluation",
        "name": "Security Agent",
        "roles": ["reviewer", "writer"],
        "tools": ["kb_search", "summarize"],
    },
    "devops_assistant": {
        "agent_type": "monitoring",
        "name": "DevOps Agent",
        "roles": ["coordinator", "writer"],
        "tools": ["datetime", "summarize"],
    },
    "meeting_assistant": {
        "agent_type": "custom",
        "name": "Meeting Assistant",
        "roles": ["writer"],
        "tools": ["summarize"],
    },
}


def list_agent_types() -> list[dict[str, Any]]:
    return [{"type": k, **v} for k, v in AGENT_TYPES.items()]


def list_templates() -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in AGENT_TEMPLATES.items()]


def get_type_defaults(agent_type: str) -> dict[str, Any]:
    return AGENT_TYPES.get(agent_type, AGENT_TYPES["custom"])


def get_template(template_id: str) -> dict[str, Any] | None:
    tpl = AGENT_TEMPLATES.get(template_id)
    if not tpl:
        return None
    return {"id": template_id, **tpl}
