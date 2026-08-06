"""Named composer recipes — human-friendly goal → graph patterns."""

from __future__ import annotations

from typing import Any

GENERIC_AUTOMATION = {
    "id": "generic_automation",
    "name": "Generic Field Automation",
    "match": ("automate", "workflow", "process"),
    "any_of": ("automate", "automation", "workflow"),
    "caps": ["cap_workflow"],
    "field": "generic",
    "description": "Universal trigger → LLM → output workflow for any field",
}

RECIPES: list[dict[str, Any]] = [
    {
        "id": "telegram_knowledge_bot",
        "name": "Telegram Knowledge Bot",
        "match": ("telegram", "bot", "knowledge"),
        "any_of": ("telegram",),
        "caps": ["cap_telegram", "cap_knowledge"],
        "field": "support",
        "description": "Answer from knowledge and reply on Telegram",
    },
    {
        "id": "email_digest",
        "name": "Email Digest",
        "match": ("digest", "email"),
        "any_of": ("digest", "weekly email", "email digest"),
        "caps": ["cap_smtp", "cap_knowledge"],
        "field": "ops",
        "description": "Summarize documents and email a digest",
    },
    {
        "id": "github_triage",
        "name": "GitHub Issue Triage",
        "match": ("github",),
        "any_of": ("github", "issue triage"),
        "caps": ["cap_github", "cap_workflow"],
        "field": "ops",
        "description": "Classify input and open or update a GitHub issue",
    },
    {
        "id": "jira_triage",
        "name": "Jira Triage",
        "match": ("jira",),
        "any_of": ("jira",),
        "caps": ["cap_jira", "cap_workflow"],
        "field": "ops",
        "description": "Create or update a Jira ticket from the goal",
    },
    {
        "id": "linear_triage",
        "name": "Linear Triage",
        "match": ("linear",),
        "any_of": ("linear",),
        "caps": ["cap_linear", "cap_workflow"],
        "field": "ops",
        "description": "Create a Linear issue from the goal",
    },
    {
        "id": "slack_notify",
        "name": "Slack Notifier",
        "match": ("slack",),
        "any_of": ("slack",),
        "caps": ["cap_slack"],
        "field": "ops",
        "description": "Draft a message and notify Slack",
    },
    {
        "id": "discord_notify",
        "name": "Discord Notifier",
        "match": ("discord",),
        "any_of": ("discord",),
        "caps": ["cap_discord"],
        "field": "ops",
        "description": "Draft a message and notify Discord",
    },
    {
        "id": "csv_etl",
        "name": "CSV / ETL Pipeline",
        "match": ("csv", "etl", "transform"),
        "any_of": ("csv", "etl", "transform", "pipeline"),
        "caps": ["cap_workflow"],
        "field": "ops",
        "description": "Transform tabular input then summarize",
    },
    {
        "id": "webhook_http",
        "name": "Webhook / HTTP Call",
        "match": ("webhook", "http"),
        "any_of": ("webhook", "http call", "call api"),
        "caps": ["cap_workflow", "cap_http"],
        "field": "sales",
        "description": "Produce a payload and POST to a webhook",
    },
    {
        "id": "multi_agent",
        "name": "Multi-Agent Supervisor",
        "match": ("multi-agent", "supervisor", "agent team"),
        "any_of": ("multi-agent", "supervisor", "agent team", "research agent"),
        "caps": ["cap_workflow", "cap_agent"],
        "field": "ops",
        "description": "Run an agent (optional knowledge) for complex goals",
    },
    {
        "id": "scheduled_job",
        "name": "Scheduled Job",
        "match": ("schedule", "cron", "daily", "weekly"),
        "any_of": ("schedule", "cron", "every day", "weekly"),
        "caps": ["cap_workflow"],
        "field": "ops",
        "description": "Workflow with schedule metadata (configure in Schedules)",
    },
    # Domain packs (existing caps only)
    {
        "id": "support_intake",
        "name": "Support Intake",
        "match": ("support", "ticket", "helpdesk", "intake"),
        "any_of": ("support ticket", "customer support", "helpdesk", "intake"),
        "caps": ["cap_knowledge", "cap_workflow", "cap_smtp"],
        "field": "support",
        "description": "Answer support questions from knowledge and email a reply",
    },
    {
        "id": "sales_lead_capture",
        "name": "Sales Lead Capture",
        "match": ("lead", "sales", "crm", "prospect"),
        "any_of": ("lead capture", "sales lead", "crm", "prospect"),
        "caps": ["cap_workflow", "cap_http", "cap_slack"],
        "field": "sales",
        "description": "Normalize lead input, optional webhook, Slack notify",
    },
    {
        "id": "hr_onboarding",
        "name": "HR Onboarding",
        "match": ("onboard", "hire", "hr", "welcome"),
        "any_of": ("onboard", "new hire", "welcome email", "hr onboarding"),
        "caps": ["cap_knowledge", "cap_smtp", "cap_workflow"],
        "field": "hr",
        "description": "Onboarding checklist from knowledge + welcome email",
    },
    {
        "id": "finance_expense",
        "name": "Finance Expense / Invoice",
        "match": ("invoice", "expense", "finance", "payment"),
        "any_of": ("invoice", "expense", "finance summary", "payment reminder"),
        "caps": ["cap_knowledge", "cap_smtp", "cap_workflow"],
        "field": "finance",
        "description": "Summarize invoices/expenses from docs and email",
    },
    {
        "id": "ops_status_report",
        "name": "Ops Status Report",
        "match": ("status report", "ops", "sla", "incident"),
        "any_of": ("status report", "ops report", "incident summary"),
        "caps": ["cap_knowledge", "cap_slack", "cap_workflow"],
        "field": "ops",
        "description": "Retrieve context, draft status, notify Slack",
    },
    {
        "id": "whatsapp_notify",
        "name": "WhatsApp Alerts",
        "match": ("whatsapp",),
        "any_of": ("whatsapp", "whats app"),
        "caps": ["cap_whatsapp", "cap_workflow"],
        "field": "ops",
        "description": "Draft a message and send via WhatsApp Cloud API",
    },
    {
        "id": "youtube_digest",
        "name": "YouTube Digest",
        "match": ("youtube",),
        "any_of": ("youtube", "yt channel"),
        "caps": ["cap_youtube", "cap_workflow", "cap_knowledge"],
        "field": "content",
        "description": "Summarize or act on YouTube channel data via API",
    },
    {
        "id": "shopify_ops",
        "name": "Shopify Ops",
        "match": ("shopify",),
        "any_of": ("shopify",),
        "caps": ["cap_shopify", "cap_workflow"],
        "field": "sales",
        "description": "Automate Shopify Admin API actions from chat",
    },
    {
        "id": "google_api",
        "name": "Google API Automation",
        "match": ("google", "sheets", "drive"),
        "any_of": ("google auth", "google oauth", "google sheets", "google drive", "google api"),
        "caps": ["cap_google", "cap_workflow"],
        "field": "ops",
        "description": "Call Google APIs with OAuth credentials from the vault",
    },
    {
        "id": "outlook_mail",
        "name": "Outlook Mail",
        "match": ("outlook", "microsoft"),
        "any_of": ("outlook", "microsoft 365", "office 365", "microsoft graph"),
        "caps": ["cap_outlook", "cap_workflow"],
        "field": "ops",
        "description": "Send or process Outlook mail via Microsoft Graph",
    },
    {
        "id": "custom_saas_api",
        "name": "Custom API / SaaS",
        "match": ("hubspot", "stripe", "notion", "salesforce", "custom api"),
        "any_of": (
            "hubspot",
            "stripe",
            "notion",
            "salesforce",
            "airtable",
            "zendesk",
            "intercom",
            "custom api",
            "third party api",
        ),
        "caps": ["cap_http", "cap_workflow"],
        "field": "ops",
        "description": "Call any SaaS/API with vault API key + base URL",
    },
    {
        "id": "content_draft",
        "name": "Content Draft",
        "match": ("blog", "content", "draft", "newsletter", "copy"),
        "any_of": ("blog", "content draft", "newsletter", "write a post"),
        "caps": ["cap_workflow", "cap_knowledge"],
        "field": "content",
        "description": "Draft content from optional knowledge",
    },
    dict(GENERIC_AUTOMATION),
]


def match_recipe(goal: str, *, fallback_generic: bool = False) -> dict[str, Any] | None:
    """Return the best matching recipe for a natural-language goal."""
    scored = score_recipe(goal)
    if scored and scored.get("score", 0) >= 2 and scored.get("id") != "generic_automation":
        out = {k: v for k, v in scored.items() if k != "score"}
        return out
    if fallback_generic:
        return dict(GENERIC_AUTOMATION)
    if scored and scored.get("score", 0) >= 3:
        out = {k: v for k, v in scored.items() if k != "score"}
        return out
    return None


def score_recipe(goal: str) -> dict[str, Any] | None:
    """Return best recipe with numeric ``score`` (0 if none)."""
    g = (goal or "").lower()
    if not g.strip():
        return None
    best: dict[str, Any] | None = None
    best_score = 0
    for recipe in RECIPES:
        if recipe.get("id") == "generic_automation":
            continue
        score = 0
        for token in recipe.get("any_of") or ():
            if token in g:
                score += 3
        for token in recipe.get("match") or ():
            if token in g:
                score += 1
        if score > best_score:
            best_score = score
            best = dict(recipe)
    # Prefer integration-specific recipes on ties (e.g. youtube over email_digest)
    if "youtube" in g:
        yt = next((r for r in RECIPES if r.get("id") == "youtube_digest"), None)
        if yt:
            yt_score = 0
            for token in yt.get("any_of") or ():
                if token in g:
                    yt_score += 3
            for token in yt.get("match") or ():
                if token in g:
                    yt_score += 1
            if yt_score >= best_score:
                best = dict(yt)
                best_score = yt_score + 1  # prefer YouTube over generic schedule/email ties
    if not best:
        return None
    best["score"] = best_score
    return best


def is_express_recipe(goal: str) -> bool:
    """High-confidence recipe match suitable for one-turn compose+test."""
    scored = score_recipe(goal)
    return bool(scored and int(scored.get("score") or 0) >= 2)


def progress_steps(*, missing_credentials: list[str] | None = None, mode: str = "workflow") -> list[dict[str, str]]:
    if mode == "agent":
        return [
            {"id": "plan", "label": "Plan"},
            {"id": "approve", "label": "Approve"},
            {"id": "run", "label": "Run agent"},
            {"id": "done", "label": "Done"},
        ]
    if missing_credentials:
        return [
            {"id": "plan", "label": "Plan"},
            {"id": "creds", "label": "Credentials (needed)"},
            {"id": "test", "label": "Test"},
            {"id": "deploy", "label": "Deploy"},
        ]
    return [
        {"id": "plan", "label": "Plan"},
        {"id": "approve", "label": "Approve"},
        {"id": "test", "label": "Test"},
        {"id": "deploy", "label": "Deploy"},
    ]
