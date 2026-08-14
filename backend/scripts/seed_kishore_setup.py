#!/usr/bin/env python3
"""Seed credentials + email/Telegram workflows for kishorevekariya70@gmail.com workspace."""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import or_

from app.database import CredentialVaultEntry, SessionLocal, User, Workflow, Workspace, WorkspaceMember, init_db
from app.crypto import hash_password
from app.services.tenancy import ensure_personal_workspace
from app.services import credential_vault as vault
from app.services.integrations import ensure_telegram_webhook_for_workflow
from app.services.workflow import run_workflow
from app.workflow_intelligence.graph.parser import parse_graph
from app.workflow_intelligence.publish_gate import check_publish_ready

USER_EMAIL = "kishorvekariya70@gmail.com"

TELEGRAM_LABEL = "Novaflow_text_bot"
TELEGRAM_TOKEN = "8851250994:AAFOUixnyPEGJbMkoba6hndMaSpw34bMjrc"

GMAIL_OAUTH_LABEL = "Oauth2"
GMAIL_CLIENT_ID = "922821659148-k0lmi2ng3lc3ka8usdksbpec5k7vd15j.apps.googleusercontent.com"
GMAIL_CLIENT_SECRET = "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"

EMAIL_FROM = "anshvekariya2007@gmail.com"
EMAIL_TO = "kishorvekariya70@gmail.com"

EMAIL_WORKFLOW_NAME = "NovaFlow Email Sender"
TELEGRAM_WORKFLOW_NAME = "NovaFlow Telegram Bot"

EMAIL_TOPICS = [
    "Government policy updates in India",
    "Weekly team productivity tips",
    "NovaFlow AI product launch announcement",
    "Cybersecurity best practices for startups",
    "Climate and renewable energy news summary",
]


def _email_graph() -> dict:
    return {
        "nodes": [
            {
                "id": "trigger",
                "type": "trigger",
                "x": 40,
                "y": 140,
                "data": {"label": "Manual run"},
            },
            {
                "id": "llm",
                "type": "llm",
                "x": 260,
                "y": 140,
                "data": {
                    "prompt": (
                        "Write a professional email.\n"
                        "Line 1 MUST be: Subject: <concise subject under 80 characters>\n"
                        "Then 2-4 short paragraphs for the body. Plain text, no markdown.\n"
                        "Topic or instruction: {{input}}"
                    ),
                },
            },
            {
                "id": "notify",
                "type": "notify",
                "x": 480,
                "y": 140,
                "data": {
                    "channel": "email",
                    "label": "Send email",
                    "to": EMAIL_TO,
                    "from": EMAIL_FROM,
                    "subject": "{{subject}}",
                    "message": "{{output}}",
                },
            },
            {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Done"}},
        ],
        "edges": [
            {"from": "trigger", "to": "llm"},
            {"from": "llm", "to": "notify"},
            {"from": "notify", "to": "output"},
        ],
    }


def _telegram_graph() -> dict:
    return {
        "nodes": [
            {
                "id": "trigger",
                "type": "trigger",
                "x": 40,
                "y": 140,
                "data": {"trigger_type": "telegram", "label": "Telegram message"},
            },
            {
                "id": "llm",
                "type": "llm",
                "x": 260,
                "y": 140,
                "data": {
                    "prompt": (
                        "You are NovaFlow_text_bot — a helpful assistant on Telegram. "
                        "Reply in under 600 characters, plain text, friendly and clear.\n"
                        "User message: {{input}}"
                    ),
                },
            },
            {
                "id": "notify",
                "type": "notify",
                "x": 480,
                "y": 140,
                "data": {
                    "channel": "telegram",
                    "label": "Telegram reply",
                    "to": "{{chat_id}}",
                    "message": "{{output}}",
                },
            },
            {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Sent"}},
        ],
        "edges": [
            {"from": "trigger", "to": "llm"},
            {"from": "llm", "to": "notify"},
            {"from": "notify", "to": "output"},
        ],
    }


def _log(msg: str) -> None:
    print(msg, flush=True)


def _ensure_kishore_user(db):
    user = db.query(User).filter(User.email == USER_EMAIL, User.delete == 0).first()
    if not user:
        user = db.query(User).filter(User.user_name == USER_EMAIL, User.delete == 0).first()
    if not user:
        _log(f"Creating user {USER_EMAIL} ...")
        user = User(
            user_name="kishorvekariya70",
            email=USER_EMAIL,
            password=hash_password("NovaFlowLocalDev1"),
            role="admin",
            email_verified=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        ensure_personal_workspace(db, user)
        _log(f"  created user id={user.user_id}")
    return user


def _find_user_workspace(db):
    user = _ensure_kishore_user(db)
    member = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.user_id)
        .first()
    )
    if not member:
        ws = db.query(Workspace).filter(Workspace.owner_id == user.user_id).first()
        if not ws:
            raise SystemExit("No workspace for user")
        workspace_id = ws.id
    else:
        workspace_id = member.workspace_id
    return user, workspace_id


def _upsert_credential(db, user_id, workspace_id, category, kind, label, fields, is_default=True):
    rows = vault.list_entries(db, workspace_id, category=category, kind=kind)
    existing = next((r for r in rows if r.label == label), None)
    if existing:
        row = vault.update_entry(db, existing, fields=fields, is_default=is_default)
        if category == "telegram":
            vault.auto_verify_telegram(db, row)
            row = vault.get_entry(db, workspace_id, row.id)
        print(f"  updated credential: {label} ({row.id}) status={row.status}", flush=True)
        return row
    row = vault.create_entry(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        category=category,
        kind=kind,
        label=label,
        fields=fields,
        is_default=is_default,
    )
    if category == "telegram" and kind == "telegram_bot":
        vault.auto_verify_telegram(db, row)
        row = vault.get_entry(db, workspace_id, row.id)
    print(f"  created credential: {label} ({row.id}) status={row.status}", flush=True)
    return row


def _upsert_workflow(db, user_id, workspace_id, name, desc, graph, publish=True):
    w = (
        db.query(Workflow)
        .filter(Workflow.workspace_id == workspace_id, Workflow.name == name)
        .first()
    )
    graph_json = json.dumps(graph)
    if not w:
        w = Workflow(
            name=name,
            desc=desc,
            graph_json=graph_json,
            user_id=user_id,
            workspace_id=workspace_id,
            status=0,
        )
        db.add(w)
        db.commit()
        db.refresh(w)
        print(f"  created workflow: {name} ({w.id})")
    else:
        w.desc = desc
        w.graph_json = graph_json
        w.update_time = __import__("datetime").datetime.utcnow()
        db.commit()
        print(f"  updated workflow: {name} ({w.id})")

    if publish:
        gate = check_publish_ready(
            parse_graph(graph_json),
            db=db,
            workspace_id=workspace_id,
        )
        if not gate.get("ready"):
            print(f"  WARN publish gate blocked {name}: {gate.get('blockers')[:2]}")
        else:
            w.status = 1
            if not w.webhook_token:
                w.webhook_token = secrets.token_urlsafe(24)
            db.commit()
            print(f"  published: {name}")
            if name == TELEGRAM_WORKFLOW_NAME:
                result = asyncio.run(
                    ensure_telegram_webhook_for_workflow(db, workspace_id, w.id, graph_json)
                )
                if result:
                    ok = result.get("ok")
                    print(f"  telegram webhook: ok={ok} url={result.get('webhook_url')}")
                    if not ok:
                        print(f"    detail: {result.get('detail')}")
    return w


async def _run_email_batch(db, workflow, user_id, workspace_id):
    results = []
    for topic in EMAIL_TOPICS:
        print(f"  running email topic: {topic[:50]}...")
        try:
            out = await run_workflow(db, workflow, user_id, topic, workspace_id)
            status = out.get("status") or "unknown"
            steps = out.get("steps") or []
            notify_step = next((s for s in steps if s.get("type") == "notify"), None)
            detail = (notify_step or {}).get("output") or out.get("output") or ""
            results.append({"topic": topic, "status": status, "detail": str(detail)[:200]})
            print(f"    -> {status}: {str(detail)[:120]}")
        except Exception as exc:
            results.append({"topic": topic, "status": "error", "detail": str(exc)[:200]})
            print(f"    -> error: {exc}")
    return results


def main():
    init_db()
    db = SessionLocal()
    try:
        user, workspace_id = _find_user_workspace(db)
        print(f"User {USER_EMAIL} (id={user.user_id}) workspace={workspace_id}", flush=True)
        print(f"Login: {USER_EMAIL} / NovaFlowLocalDev1  OR Sign in with Google", flush=True)

        print("Credentials:")
        _upsert_credential(
            db,
            user.user_id,
            workspace_id,
            "telegram",
            "telegram_bot",
            TELEGRAM_LABEL,
            {"bot_token": TELEGRAM_TOKEN},
        )
        _upsert_credential(
            db,
            user.user_id,
            workspace_id,
            "email",
            "gmail_oauth",
            GMAIL_OAUTH_LABEL,
            {
                "client_id": GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
            },
        )

        print("Workflows:")
        email_wf = _upsert_workflow(
            db,
            user.user_id,
            workspace_id,
            EMAIL_WORKFLOW_NAME,
            f"LLM writes subject + body, sends from {EMAIL_FROM} to {EMAIL_TO}",
            _email_graph(),
        )
        telegram_wf = _upsert_workflow(
            db,
            user.user_id,
            workspace_id,
            TELEGRAM_WORKFLOW_NAME,
            "Telegram trigger -> LLM -> reply via Novaflow_text_bot",
            _telegram_graph(),
        )

        print("Email batch (5 sends):")
        email_results = asyncio.run(_run_email_batch(db, email_wf, user.user_id, workspace_id))

        print("\n=== SUMMARY ===", flush=True)
        print(f"Workspace id (for nf_workspace_id): {workspace_id}", flush=True)
        print(f"Email workflow id: {email_wf.id}", flush=True)
        print(f"Telegram workflow id: {telegram_wf.id}", flush=True)
        print(f"Telegram webhook path: /api/v1/integrations/telegram/webhook/{telegram_wf.id}")
        for r in email_results:
            print(f"  email [{r['status']}] {r['topic'][:40]} — {r['detail'][:80]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
