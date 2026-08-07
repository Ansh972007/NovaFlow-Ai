"""Single source of truth for workflow node types, field schemas, and defaults."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

# Credential vault bindings for HTTP auth modes
HTTP_AUTH_VAULT_MAP: dict[str, tuple[str, str]] = {
    "youtube": ("youtube", "youtube_api"),
    "google": ("google", "google_oauth"),
    "google_api": ("google", "google_oauth"),
    "shopify": ("shopify", "shopify_admin"),
    "custom": ("custom", "custom"),
    "outlook": ("outlook", "microsoft_graph"),
}

NOTIFY_CHANNEL_VAULT_MAP: dict[str, tuple[str, str]] = {
    "telegram": ("telegram", "telegram_bot"),
    "email": ("email", "gmail_smtp"),
    "slack": ("slack", "slack_webhook"),
    "discord": ("discord", "discord_webhook"),
    "webhook": ("webhook", "generic_webhook"),
}

INTEGRATION_VAULT_MAP: dict[str, tuple[str, str]] = {
    "jira": ("jira", "jira_cloud"),
    "github": ("github", "github_pat"),
    "linear": ("linear", "linear_api"),
}


def _field(
    key: str,
    label: str,
    field_type: str = "text",
    *,
    required: bool = False,
    default: Any = None,
    options: list[dict[str, str]] | None = None,
    show_when: dict[str, str] | None = None,
    vault_category: str | None = None,
    vault_kind: str | None = None,
    placeholder: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "key": key,
        "label": label,
        "field_type": field_type,
        "required": required,
    }
    if default is not None:
        out["default"] = default
    if options:
        out["options"] = options
    if show_when:
        out["show_when"] = show_when
    if vault_category:
        out["vault_category"] = vault_category
    if vault_kind:
        out["vault_kind"] = vault_kind
    if placeholder:
        out["placeholder"] = placeholder
    return out


BUILTIN_NODE_SCHEMAS: dict[str, dict[str, Any]] = {
    "trigger": {
        "type": "trigger",
        "label": "Trigger",
        "category": "builtin",
        "icon": "trigger",
        "description": "Workflow entry point — receives user input.",
        "fields": [
            _field("label", "Label", default="Trigger"),
            _field(
                "trigger_type",
                "Trigger type",
                "select",
                default="manual",
                options=[
                    {"value": "manual", "label": "Manual / chat input"},
                    {"value": "webhook", "label": "Webhook"},
                    {"value": "telegram", "label": "Telegram message"},
                    {"value": "schedule", "label": "Scheduled (cron)"},
                ],
            ),
            _field(
                "description",
                "What starts this workflow?",
                "textarea",
                placeholder="e.g. User asks a question in chat, or POST to webhook URL",
            ),
            _field(
                "webhook_hint",
                "Webhook note",
                show_when={"trigger_type": "webhook"},
                placeholder="Publish workflow to get webhook URL in Deploy panel",
            ),
            _field(
                "telegram_chat_filter",
                "Telegram chat ID filter",
                show_when={"trigger_type": "telegram"},
                placeholder="Optional — only run for this chat_id",
            ),
        ],
    },
    "retrieve": {
        "type": "retrieve",
        "label": "Retrieve",
        "category": "builtin",
        "icon": "retrieve",
        "description": "Search a knowledge base for relevant chunks.",
        "fields": [
            _field("knowledge_id", "Knowledge base", "knowledge", required=True),
            _field("query", "Search query", "textarea", default="{{input}}", placeholder="{{input}}"),
            _field("limit", "Chunk limit", "number", default=6),
        ],
    },
    "llm": {
        "type": "llm",
        "label": "LLM",
        "category": "builtin",
        "icon": "llm",
        "description": "Generate text with the workspace LLM.",
        "fields": [
            _field("label", "Label", default="LLM"),
            _field(
                "user_prompt",
                "User message template",
                "textarea",
                default="{{input}}",
                placeholder="{{input}} — question or payload for the model",
            ),
            _field(
                "prompt",
                "System prompt",
                "textarea",
                default=(
                    "Answer clearly. Prefer structure: direct answer, then short supporting bullets. "
                    "If context is missing, say what is unknown."
                ),
            ),
            _field("temperature", "Temperature", "number", default=0.7),
        ],
    },
    "output": {
        "type": "output",
        "label": "Output",
        "category": "builtin",
        "icon": "output",
        "description": "Final workflow output node.",
        "fields": [
            _field("label", "Label", default="Output"),
            _field(
                "format",
                "Output format",
                "select",
                default="text",
                options=[
                    {"value": "text", "label": "Plain text"},
                    {"value": "markdown", "label": "Markdown"},
                    {"value": "json", "label": "JSON (structured)"},
                ],
            ),
        ],
    },
    "transform": {
        "type": "transform",
        "label": "Transform",
        "category": "builtin",
        "icon": "transform",
        "description": "Template transform on workflow context.",
        "fields": [
            _field("template", "Template", "textarea", default="{{input}}", placeholder="{{input}}"),
        ],
    },
    "condition": {
        "type": "condition",
        "label": "Condition",
        "category": "builtin",
        "icon": "condition",
        "description": "Branch on keyword match in input.",
        "fields": [
            _field("keyword", "Keyword", required=True),
            _field("then_text", "Then text", "textarea", default="{{input}}"),
            _field("else_text", "Else text", "textarea", default=""),
        ],
    },
    "http": {
        "type": "http",
        "label": "HTTP",
        "category": "builtin",
        "icon": "http",
        "description": "HTTP request with optional vault authentication.",
        "fields": [
            _field("label", "Label", default="HTTP request"),
            _field("url", "URL", required=True, default="", placeholder="https://api.example.com/data?q={{input}}"),
            _field(
                "method",
                "Method",
                "select",
                default="GET",
                options=[
                    {"value": "GET", "label": "GET"},
                    {"value": "POST", "label": "POST"},
                    {"value": "PUT", "label": "PUT"},
                    {"value": "DELETE", "label": "DELETE"},
                ],
            ),
            _field(
                "auth",
                "Auth",
                "select",
                default="custom",
                options=[
                    {"value": "custom", "label": "Custom API (vault)"},
                    {"value": "youtube", "label": "YouTube"},
                    {"value": "google", "label": "Google"},
                    {"value": "shopify", "label": "Shopify"},
                    {"value": "outlook", "label": "Outlook"},
                ],
            ),
            _field(
                "credential_id",
                "Credential (vault)",
                "credential",
                vault_category="custom",
                vault_kind="custom",
            ),
            _field(
                "headers",
                "Headers (JSON)",
                "textarea",
                placeholder='{"Accept": "application/json"}',
            ),
            _field(
                "body",
                "Request body (JSON)",
                "textarea",
                show_when={"method": "POST"},
                placeholder='{"query": "{{input}}"}',
            ),
            _field(
                "body",
                "Request body (JSON)",
                "textarea",
                show_when={"method": "PUT"},
                placeholder='{"query": "{{input}}"}',
            ),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
    "notify": {
        "type": "notify",
        "label": "Notify",
        "category": "builtin",
        "icon": "notify",
        "description": "Send notification via Telegram, email, Slack, or Discord.",
        "fields": [
            _field(
                "channel",
                "Channel",
                "select",
                default="telegram",
                options=[
                    {"value": "telegram", "label": "Telegram"},
                    {"value": "email", "label": "Email / Gmail"},
                    {"value": "slack", "label": "Slack"},
                    {"value": "discord", "label": "Discord"},
                    {"value": "webhook", "label": "Webhook"},
                ],
            ),
            _field(
                "from",
                "From (sender email)",
                show_when={"channel": "email"},
                placeholder="Uses Gmail credential default if empty",
            ),
            _field(
                "to",
                "To (recipient)",
                required=True,
                show_when={"channel": "email"},
                default="{{email}}",
                placeholder="friend@example.com or {{email}}",
            ),
            _field(
                "subject",
                "Subject",
                show_when={"channel": "email"},
                default="NovaFlow",
            ),
            _field(
                "message",
                "Email body",
                "textarea",
                show_when={"channel": "email"},
                default="{{output}}",
            ),
            _field(
                "credential_id",
                "Gmail / SMTP credential",
                "credential",
                show_when={"channel": "email"},
                vault_category="email",
                vault_kind="gmail_smtp",
            ),
            _field(
                "to",
                "Chat ID",
                required=True,
                show_when={"channel": "telegram"},
                default="{{chat_id}}",
                placeholder="{{chat_id}}",
            ),
            _field(
                "message",
                "Message text",
                "textarea",
                show_when={"channel": "telegram"},
                default="{{output}}",
            ),
            _field(
                "bot_token",
                "Bot token (optional)",
                show_when={"channel": "telegram"},
                placeholder="Uses vault default if empty",
            ),
            _field(
                "credential_id",
                "Telegram bot credential",
                "credential",
                show_when={"channel": "telegram"},
                vault_category="telegram",
                vault_kind="telegram_bot",
            ),
            _field(
                "to",
                "Slack channel or webhook URL",
                show_when={"channel": "slack"},
                placeholder="#alerts or https://hooks.slack.com/...",
            ),
            _field(
                "subject",
                "Notification title",
                show_when={"channel": "slack"},
                default="NovaFlow",
            ),
            _field(
                "message",
                "Message",
                "textarea",
                show_when={"channel": "slack"},
                default="{{output}}",
            ),
            _field(
                "credential_id",
                "Slack credential",
                "credential",
                show_when={"channel": "slack"},
                vault_category="slack",
                vault_kind="slack_webhook",
            ),
            _field(
                "to",
                "Discord webhook URL",
                show_when={"channel": "discord"},
                placeholder="https://discord.com/api/webhooks/...",
            ),
            _field(
                "subject",
                "Embed title",
                show_when={"channel": "discord"},
                default="NovaFlow",
            ),
            _field(
                "message",
                "Message",
                "textarea",
                show_when={"channel": "discord"},
                default="{{output}}",
            ),
            _field(
                "credential_id",
                "Discord credential",
                "credential",
                show_when={"channel": "discord"},
                vault_category="discord",
                vault_kind="discord_webhook",
            ),
            _field(
                "to",
                "Webhook URL",
                required=True,
                show_when={"channel": "webhook"},
                placeholder="https://hooks.example.com/notify",
            ),
            _field(
                "subject",
                "Payload title",
                show_when={"channel": "webhook"},
                default="NovaFlow",
            ),
            _field(
                "message",
                "Payload body",
                "textarea",
                show_when={"channel": "webhook"},
                default="{{output}}",
            ),
        ],
    },
    "jira": {
        "type": "jira",
        "label": "Jira",
        "category": "builtin",
        "icon": "jira",
        "description": "Create or update Jira Cloud issues.",
        "fields": [
            _field(
                "action",
                "Action",
                "select",
                default="create",
                options=[
                    {"value": "create", "label": "Create issue"},
                    {"value": "update", "label": "Update issue"},
                ],
            ),
            _field(
                "credential_id",
                "Jira credential",
                "credential",
                vault_category="jira",
                vault_kind="jira_cloud",
            ),
            _field("project_key", "Project key", required=True, default="NF", show_when={"action": "create"}),
            _field("issue_type", "Issue type", default="Task", show_when={"action": "create"}),
            _field("priority", "Priority", show_when={"action": "create"}, placeholder="Medium, High, Low"),
            _field("issue_key", "Issue key", required=True, show_when={"action": "update"}, placeholder="NF-123"),
            _field("summary", "Summary", default="{{output}}"),
            _field("description", "Description", "textarea", default="{{input}}"),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
    "github": {
        "type": "github",
        "label": "GitHub",
        "category": "builtin",
        "icon": "github",
        "description": "Create or update GitHub issues.",
        "fields": [
            _field(
                "action",
                "Action",
                "select",
                default="create",
                options=[
                    {"value": "create", "label": "Create issue"},
                    {"value": "update", "label": "Update issue"},
                ],
            ),
            _field(
                "credential_id",
                "GitHub credential",
                "credential",
                vault_category="github",
                vault_kind="github_pat",
            ),
            _field("repo", "Repo (owner/name)", placeholder="Blank = default from credential"),
            _field("issue_number", "Issue number", required=True, show_when={"action": "update"}),
            _field("title", "Title", default="{{output}}"),
            _field("body", "Body", "textarea", default="{{input}}"),
            _field("labels", "Labels (comma-separated)", default="bug", show_when={"action": "create"}),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
    "linear": {
        "type": "linear",
        "label": "Linear",
        "category": "builtin",
        "icon": "linear",
        "description": "Create or update Linear issues.",
        "fields": [
            _field(
                "action",
                "Action",
                "select",
                default="create",
                options=[
                    {"value": "create", "label": "Create issue"},
                    {"value": "update", "label": "Update issue"},
                ],
            ),
            _field(
                "credential_id",
                "Linear credential",
                "credential",
                vault_category="linear",
                vault_kind="linear_api",
            ),
            _field("team_id", "Team ID", show_when={"action": "create"}, placeholder="Blank = credential default"),
            _field("issue_id", "Issue ID", required=True, show_when={"action": "update"}),
            _field("title", "Title", default="{{output}}"),
            _field("description", "Description", "textarea", default="{{input}}"),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
    "loop": {
        "type": "loop",
        "label": "Loop",
        "category": "builtin",
        "icon": "loop",
        "description": "Iterate over input items with bounded LLM calls.",
        "fields": [
            _field("max", "Max items", "number", default=5),
            _field(
                "prompt",
                "Per-item prompt",
                "textarea",
                default="For this item, return one compact line: RESULT: <outcome> | WHY: <short reason>\nItem: {{item}}",
            ),
            _field("separator", "Item separator", default="\n"),
            _field("concurrency", "Concurrency", "number", default=3),
            _field(
                "system",
                "System prompt",
                "textarea",
                default="Produce compact, consistent results for each item. No preamble — only the requested format.",
            ),
            _field("merge", "Merge results with LLM", "checkbox", default=True),
        ],
    },
    "parallel": {
        "type": "parallel",
        "label": "Parallel",
        "category": "builtin",
        "icon": "parallel",
        "description": "Run multiple LLM perspectives in parallel.",
        "fields": [
            _field("branches", "Branches", default=["Summary", "Key points", "Actions"]),
        ],
    },
    "human": {
        "type": "human",
        "label": "Human",
        "category": "builtin",
        "icon": "human",
        "description": "Pause for human review and approval.",
        "fields": [
            _field("message", "Review message", "textarea", default="Review and approve before finalize:\n\n{{output}}"),
            _field("require_approval", "Require approval", "checkbox", default=True),
        ],
    },
    "agent": {
        "type": "agent",
        "label": "Agent",
        "category": "builtin",
        "icon": "agent",
        "description": "Multi-tool agent step.",
        "fields": [
            _field("tools", "Tools (comma-separated)", default=["summarize"]),
            _field(
                "prompt",
                "System prompt",
                "textarea",
                default=(
                    "You are a capable NovaFlow agent. Use tool results as evidence. "
                    "Answer with: Summary · Details · Confidence (high/med/low)."
                ),
            ),
            _field("knowledge_id", "Knowledge base (kb_search)", "knowledge", show_when={"tools_contains": "kb_search"}),
        ],
    },
    "subgraph": {
        "type": "subgraph",
        "label": "Subgraph",
        "category": "builtin",
        "icon": "subgraph",
        "description": "Run another published workflow as a sub-step.",
        "fields": [
            _field("workflow_id", "Workflow", "workflow", required=True),
            _field("label", "Label", default="Sub-workflow"),
        ],
    },
    "api_node": {
        "type": "api_node",
        "label": "API Node",
        "category": "api",
        "icon": "api",
        "description": "Execute a published API node from the node library.",
        "fields": [
            _field("node_def_id", "Library node", "node_def", required=True),
            _field("label", "Label"),
            _field(
                "credential_id",
                "Credential override",
                "credential",
                vault_category="custom",
                vault_kind="custom",
            ),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
    "component_node": {
        "type": "component_node",
        "label": "AI Component",
        "category": "dynamic",
        "icon": "component",
        "description": "Run an AI-generated disk component.",
        "fields": [
            _field("component_name", "Component", required=True),
            _field("set_output", "Set workflow output", "checkbox", default=True),
        ],
    },
}


def get_known_node_types() -> frozenset[str]:
    return frozenset(BUILTIN_NODE_SCHEMAS.keys())


def get_allowed_planner_types() -> frozenset[str]:
    return get_known_node_types()


def merge_node_data_with_defaults(node_type: str, data: dict[str, Any] | None) -> dict[str, Any]:
    """Fill missing node.data keys from registry defaults (builder + persisted graphs)."""
    defaults = default_data_for_type(node_type)
    merged = dict(defaults)
    for key, val in (data or {}).items():
        if val is not None:
            merged[key] = val
    return merged


def get_schema(node_type: str) -> dict[str, Any] | None:
    return BUILTIN_NODE_SCHEMAS.get(str(node_type or "").lower())


def default_data_for_type(node_type: str) -> dict[str, Any]:
    schema = get_schema(node_type)
    if not schema:
        return {}
    data: dict[str, Any] = {}
    for f in schema.get("fields") or []:
        key = f.get("key")
        if not key:
            continue
        if "default" in f:
            data[key] = f["default"]
        elif f.get("field_type") == "credential":
            data[key] = ""
    return data


def get_builtin_palette_with_schemas() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ntype in (
        "trigger",
        "retrieve",
        "llm",
        "output",
        "transform",
        "condition",
        "http",
        "notify",
        "jira",
        "github",
        "linear",
        "loop",
        "parallel",
        "human",
        "agent",
        "subgraph",
    ):
        schema = BUILTIN_NODE_SCHEMAS[ntype]
        out.append(
            {
                "type": schema["type"],
                "label": schema["label"],
                "category": schema["category"],
                "icon": schema.get("icon"),
                "description": schema.get("description"),
                "fields": schema.get("fields") or [],
                "defaults": default_data_for_type(ntype),
            }
        )
    return out


def _input_to_field(inp: dict[str, Any]) -> dict[str, Any]:
    key = str(inp.get("key") or inp.get("name") or "").strip()
    if not key:
        return {}
    label = str(inp.get("label") or inp.get("name") or key)
    ftype = str(inp.get("type") or "text").lower()
    field_type = "text"
    if ftype in ("number", "integer", "float"):
        field_type = "number"
    elif ftype in ("boolean", "bool", "checkbox"):
        field_type = "checkbox"
    elif ftype in ("textarea", "text"):
        field_type = "textarea"
    return _field(
        key,
        label,
        field_type,
        required=bool(inp.get("required")),
        default=inp.get("default"),
        placeholder=str(inp.get("placeholder") or "") or None,
    )


def component_to_palette_entry(component: dict[str, Any]) -> dict[str, Any]:
    name = str(component.get("name") or "").strip()
    fields: list[dict[str, Any]] = [
        _field("component_name", "Component", default=name),
        _field("set_output", "Set workflow output", "checkbox", default=True),
    ]
    for inp in component.get("inputs") or []:
        if isinstance(inp, dict):
            f = _input_to_field(inp)
            if f:
                fields.append(f)
    config = component.get("configuration") or {}
    if config.get("url") or config.get("credential_id") or config.get("auth"):
        fields.append(
            _field(
                "credential_id",
                "Credential",
                "credential",
                vault_category="custom",
                vault_kind="custom",
            )
        )
    defaults = default_data_for_type("component_node")
    defaults["component_name"] = name
    for inp in component.get("inputs") or []:
        if isinstance(inp, dict) and inp.get("default") is not None:
            k = inp.get("key") or inp.get("name")
            if k:
                defaults[k] = inp.get("default")
    return {
        "type": "component_node",
        "name": name,
        "label": name,
        "category": "dynamic",
        "icon": "component",
        "description": str(component.get("description") or f"AI component: {name}"),
        "component_type": component.get("type") or "custom",
        "fields": fields,
        "defaults": defaults,
        "has_http": bool(config.get("url")),
    }


@lru_cache(maxsize=1)
def _component_dir() -> str:
    return os.environ.get("COMPONENT_DIR", "components")


def get_component_discovery():
    from app.services.dynamic_component_creator import ComponentDiscovery

    return ComponentDiscovery(_component_dir())


def list_dynamic_components() -> list[dict[str, Any]]:
    discovery = get_component_discovery()
    return [component_to_palette_entry(c) for c in discovery.list_all_components()]


def planner_type_summary() -> str:
    lines: list[str] = []
    for ntype, schema in BUILTIN_NODE_SCHEMAS.items():
        if ntype in ("api_node", "component_node"):
            continue
        req = [
            f["key"]
            for f in schema.get("fields") or []
            if f.get("required") and f.get("field_type") != "credential"
        ]
        req_str = ", ".join(req) if req else "none"
        lines.append(f"- {ntype}: required fields: {req_str}")
    return "\n".join(lines)


def _field_visible(f: dict[str, Any], ctx: dict[str, Any]) -> bool:
    show_when = f.get("show_when") or {}
    if not show_when:
        return True
    for k, v in show_when.items():
        if k == "tools_contains":
            tools = ctx.get("tools") or []
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(",") if t.strip()]
            if v not in tools:
                return False
        elif str(ctx.get(k) or "") != str(v):
            return False
    return True


def validate_node_data(
    node_type: str,
    data: dict[str, Any],
    *,
    show_when_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Return list of {field, message} for missing required fields."""
    schema = get_schema(node_type)
    if not schema:
        return []
    ctx = dict(data or {})
    if show_when_context:
        ctx.update(show_when_context)
    issues: list[dict[str, str]] = []
    for f in schema.get("fields") or []:
        if not f.get("required"):
            continue
        if not _field_visible(f, ctx):
            continue
        key = f.get("key")
        if not key:
            continue
        val = data.get(key)
        empty = val is None or (isinstance(val, str) and not val.strip())
        if key == "knowledge_id" and val is None:
            empty = True
        if empty:
            issues.append({"field": key, "message": f"Missing required field: {f.get('label') or key}"})
    return issues


def credential_binding_for_node(node_type: str, data: dict[str, Any]) -> tuple[str, str] | None:
    ntype = str(node_type or "").lower()
    data = data or {}
    if ntype == "http":
        auth = (data.get("auth") or "custom").strip().lower()
        return HTTP_AUTH_VAULT_MAP.get(auth, ("custom", "custom"))
    if ntype == "notify":
        channel = (data.get("channel") or "telegram").strip().lower()
        return NOTIFY_CHANNEL_VAULT_MAP.get(channel)
    if ntype in INTEGRATION_VAULT_MAP:
        return INTEGRATION_VAULT_MAP[ntype]
    if ntype == "api_node":
        return ("custom", "custom")
    if ntype == "component_node":
        return ("custom", "custom")
    return None
