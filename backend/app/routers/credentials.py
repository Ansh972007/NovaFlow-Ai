"""Credentials vault API — multi-slot secrets per workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.schemas import fail, ok
from app.security.rbac import Permission
from app.services import credential_vault as vault

router = APIRouter(prefix="/credentials", tags=["Credentials"])


@router.get("/catalog")
def catalog(ctx=Depends(require_permission(Permission.INTEGRATION_READ))):
    return ok(vault.get_catalog())


@router.get("/overview")
def credentials_overview(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    return ok(vault.overview(db, ctx.workspace_id))


@router.get("")
@router.get("/")
def list_credentials(
    category: str | None = None,
    kind: str | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    rows = vault.list_entries(db, ctx.workspace_id, category=category, kind=kind)
    return ok([vault.serialize_entry(r) for r in rows])


@router.post("")
@router.post("/")
def create_credential(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    category = (body.get("category") or "").strip()
    kind = (body.get("kind") or "").strip()
    label = (body.get("label") or "default").strip()
    fields = body.get("fields") if isinstance(body.get("fields"), dict) else {}
    is_default = bool(body.get("is_default"))
    if not category or not kind:
        return fail(400, "category and kind are required")
    row = vault.create_entry(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        category=category,
        kind=kind,
        label=label,
        fields=fields,
        is_default=is_default,
    )
    ctx.audit("credential.created", resource_type="credential", resource_id=row.id)
    return ok(vault.serialize_entry(row))


@router.get("/{entry_id}")
def get_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_READ)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    return ok(vault.serialize_entry(row))


@router.patch("/{entry_id}")
def patch_credential(
    entry_id: str,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    fields = body.get("fields") if isinstance(body.get("fields"), dict) else None
    label = body.get("label")
    is_default = body.get("is_default")
    if is_default is not None:
        is_default = bool(is_default)
    row = vault.update_entry(
        db,
        row,
        fields=fields,
        label=label if label is not None else None,
        is_default=is_default,
    )
    ctx.audit("credential.updated", resource_type="credential", resource_id=row.id)
    return ok(vault.serialize_entry(row))


@router.delete("/{entry_id}")
def delete_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    vault.delete_entry(db, row)
    ctx.audit("credential.deleted", resource_type="credential", resource_id=entry_id)
    return ok(None)


@router.post("/{entry_id}/set-default")
def set_default_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    row = vault.set_default(db, row)
    return ok(vault.serialize_entry(row))


@router.post("/{entry_id}/verify")
async def verify_credential(
    entry_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.INTEGRATION_WRITE)),
):
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    if not row:
        return fail(404, "Credential not found")
    fields = vault.resolve_fields(
        db, ctx.workspace_id, category=row.category, kind=row.kind, credential_id=row.id
    )
    detail = "ok"
    status = "ok"
    try:
        if row.category == "telegram" and fields.get("bot_token"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"https://api.telegram.org/bot{fields['bot_token']}/getMe")
                data = r.json()
                if not data.get("ok"):
                    raise ValueError(data.get("description") or "Telegram verify failed")
                detail = f"@{data.get('result', {}).get('username') or 'bot'}"
                if data.get("result", {}).get("username"):
                    vault.update_entry(
                        db,
                        row,
                        fields={"bot_username": data["result"]["username"]},
                    )
        elif row.category == "llm" and fields.get("api_key"):
            import httpx

            base = (fields.get("base_url") or "https://api.openai.com/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {fields['api_key']}"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"LLM verify failed ({r.status_code})")
                detail = "models reachable"
        elif row.category == "slack" and fields.get("webhook_url"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    fields["webhook_url"],
                    json={"text": "NovaFlow credentials verify ✅"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"Slack webhook failed ({r.status_code})")
                detail = "webhook accepted"
        elif row.category == "discord" and fields.get("webhook_url"):
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    fields["webhook_url"],
                    json={"content": "NovaFlow credentials verify ✅"},
                )
                if r.status_code >= 400:
                    raise ValueError(f"Discord webhook failed ({r.status_code})")
                detail = "webhook accepted"
        elif row.category == "email":
            detail = "fields present (send a digest/test email to fully verify)"
        else:
            detail = "stored"
        vault.update_entry(db, row, status="ok")
    except Exception as exc:
        status = "error"
        detail = str(exc)[:300]
        vault.update_entry(db, row, status="error")
    row = vault.get_entry(db, ctx.workspace_id, entry_id)
    return ok({"status": status, "detail": detail, "credential": vault.serialize_entry(row)})
