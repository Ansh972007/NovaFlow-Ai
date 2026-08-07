"""Live credential dry-run probes for sandbox / approve flows."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from app.sandbox.twin import _iter_nodes
from app.services import credential_vault as vault
from app.services.integrations import get_telegram_bot_info
from app.services.gmail_jira import jira_verify
from app.services.linear_issues import linear_verify
from app.services.workflow_http_auth import probe_http_auth


NOTIFY_PROBE_MAP: dict[str, tuple[str, str]] = {
    "email": ("email", "gmail_smtp"),
    "telegram": ("telegram", "telegram_bot"),
    "slack": ("slack", "slack_webhook"),
    "discord": ("discord", "discord_webhook"),
    "whatsapp": ("whatsapp", "whatsapp_cloud"),
}


def _auth_kinds_from_graph(graph: dict[str, Any]) -> list[tuple[str, str | None]]:
    kinds: list[tuple[str, str | None]] = []
    for _nid, node in _iter_nodes(graph or {}):
        ntype = str(node.get("type") or "").lower()
        data = node.get("data") or {}
        if ntype == "http":
            auth = (data.get("auth") or "").strip().lower()
            if auth:
                cred_id = (data.get("credential_id") or "").strip() or None
                kinds.append((auth, cred_id))
        elif ntype == "notify":
            channel = (data.get("channel") or "").strip().lower()
            cat_kind = NOTIFY_PROBE_MAP.get(channel)
            cred_id = (data.get("credential_id") or "").strip() or None
            if cat_kind:
                kinds.append((channel, cred_id))
    return kinds


async def _probe_notify_channel(
    db: Session,
    workspace_id: int,
    channel: str,
    credential_id: str | None,
) -> dict[str, Any]:
    ch = (channel or "").lower()
    if ch == "telegram":
        result = await get_telegram_bot_info(db, workspace_id)
        return {"ok": result.get("ok"), "detail": result.get("detail") or "Telegram probe failed"}
    if ch == "slack" or ch == "discord":
        fields = vault.resolve_fields(
            db,
            workspace_id,
            category=ch,
            kind=f"{ch}_webhook",
            credential_id=credential_id,
        )
        if fields.get("webhook_url"):
            return {"ok": True, "detail": f"{ch} webhook configured"}
        return {"ok": False, "detail": f"{ch} webhook missing in vault"}
    if ch == "email":
        from app.services.workspace_integrations import resolve_smtp_config

        smtp = resolve_smtp_config(db, workspace_id, credential_id=credential_id)
        if smtp.get("host") and smtp.get("password"):
            return {"ok": True, "detail": "SMTP credentials configured"}
        return {"ok": False, "detail": "SMTP credentials incomplete"}
    if ch == "whatsapp":
        # Dry-run only checks vault presence; avoid sending a real message.
        fields = vault.resolve_fields(
            db,
            workspace_id,
            category="whatsapp",
            kind="whatsapp_cloud",
            credential_id=credential_id,
        )
        if fields.get("access_token") and fields.get("phone_number_id"):
            return {"ok": True, "detail": "WhatsApp Cloud credentials configured"}
        return {"ok": False, "detail": "WhatsApp access token or phone number ID missing"}
    return {"ok": True, "detail": f"No live probe for notify channel {ch}"}


async def _probe_auth_kind(
    db: Session,
    workspace_id: int,
    auth_kind: str,
    credential_id: str | None,
) -> dict[str, Any]:
    kind = (auth_kind or "").lower()
    if kind in ("jira", "cap_jira"):
        return await jira_verify(db, workspace_id)
    if kind in ("linear", "cap_linear"):
        return await linear_verify(db, workspace_id)
    if kind in NOTIFY_PROBE_MAP:
        return await _probe_notify_channel(db, workspace_id, kind, credential_id)
    return await probe_http_auth(db, workspace_id, kind, credential_id=credential_id)


async def run_graph_credential_probes(
    db: Session,
    workspace_id: int,
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for auth_kind, cred_id in _auth_kinds_from_graph(graph):
        key = f"{auth_kind}:{cred_id or ''}"
        if key in seen:
            continue
        seen.add(key)
        result = await _probe_auth_kind(db, workspace_id, auth_kind, cred_id)
        probes.append(
            {
                "auth_kind": auth_kind,
                "credential_id": cred_id,
                "ok": bool(result.get("ok")),
                "detail": result.get("detail") or "",
            }
        )
        if cred_id and not result.get("ok"):
            try:
                from app.services import credential_vault as vault

                row = vault.get_entry(db, workspace_id, cred_id)
                if row:
                    vault.update_entry(db, row, status="failed")
            except Exception:
                pass
        elif cred_id and result.get("ok"):
            try:
                from app.services import credential_vault as vault

                row = vault.get_entry(db, workspace_id, cred_id)
                if row:
                    vault.update_entry(db, row, status="ok")
            except Exception:
                pass
    return probes


def check_credential_probe(
    db: Session | None,
    workspace_id: int | None,
    graph: dict[str, Any],
    *,
    missing_credentials: list[str] | None = None,
) -> dict[str, Any]:
    if not db or not workspace_id:
        return {
            "id": "credential_probe",
            "name": "Credential probe",
            "status": "passed",
            "message": "Skipped (no workspace context)",
        }
    if missing_credentials:
        return {
            "id": "credential_probe",
            "name": "Credential probe",
            "status": "warn",
            "message": f"Missing credentials — live probe skipped: {', '.join(missing_credentials[:4])}",
            "missing_credentials": missing_credentials,
        }
    try:
        from app.runtime.async_bridge import run_coro_sync

        probes = run_coro_sync(run_graph_credential_probes(db, workspace_id, graph))
    except Exception as exc:
        return {
            "id": "credential_probe",
            "name": "Credential probe",
            "status": "failed",
            "message": str(exc)[:200],
        }
    if not probes:
        return {
            "id": "credential_probe",
            "name": "Credential probe",
            "status": "passed",
            "message": "No integration nodes requiring live credentials",
        }
    failed = [p for p in probes if not p.get("ok")]
    if failed:
        return {
            "id": "credential_probe",
            "name": "Credential probe",
            "status": "failed",
            "message": failed[0].get("detail") or "Credential probe failed",
            "probes": probes,
        }
    return {
        "id": "credential_probe",
        "name": "Credential probe",
        "status": "passed",
        "message": f"Live credential checks passed ({len(probes)})",
        "probes": probes,
    }
