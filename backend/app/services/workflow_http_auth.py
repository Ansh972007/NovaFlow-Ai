"""Vault-aware HTTP auth for workflow http nodes (YouTube, Google, Shopify, custom)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy.orm import Session

from app.security.ssrf import assert_safe_url, SafeUrlError
from app.services import credential_vault as vault

AUTH_VAULT_MAP: dict[str, tuple[str, str]] = {
    "youtube": ("youtube", "youtube_api"),
    "google": ("google", "google_oauth"),
    "google_api": ("google", "google_oauth"),
    "shopify": ("shopify", "shopify_admin"),
    "custom": ("custom", "custom"),
    "outlook": ("outlook", "microsoft_graph"),
}

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def resolve_http_auth(
    db: Session,
    workspace_id: int | None,
    auth_kind: str,
    *,
    credential_id: str | None = None,
) -> dict[str, Any]:
    kind_key = (auth_kind or "").strip().lower() or "custom"
    category, kind = AUTH_VAULT_MAP.get(kind_key, ("custom", "custom"))
    fields: dict[str, Any] = {}
    resolved_id: str | None = None
    if db and workspace_id:
        row = None
        if credential_id:
            row = vault.get_entry(db, workspace_id, credential_id)
        if not row:
            row = vault.get_default(db, workspace_id, category=category, kind=kind)
        if row:
            resolved_id = row.id
            fields = vault.resolve_fields(
                db,
                workspace_id,
                category=row.category,
                kind=row.kind,
                credential_id=row.id,
            )
    return {
        "auth_kind": kind_key,
        "category": category,
        "kind": kind,
        "credential_id": resolved_id,
        "fields": fields,
    }


def _apply_url_templates(url: str, fields: dict[str, Any]) -> str:
    out = url or ""
    shop = (fields.get("shop") or "").strip()
    if shop and not shop.startswith("http"):
        shop = f"https://{shop.lstrip('/')}"
    base = (fields.get("base_url") or "").strip().rstrip("/")
    webhook = (fields.get("webhook_url") or "").strip()
    replacements = {
        "shop": shop,
        "base_url": base,
        "webhook_url": webhook,
    }
    for key, val in replacements.items():
        if val:
            out = out.replace(f"{{{{{key}}}}}", val)
    return out


def _append_query_param(url: str, param: str, value: str) -> str:
    if not value:
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs[param] = [value]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


async def _refresh_google_access(fields: dict[str, Any]) -> str:
    access = (fields.get("access_token") or "").strip()
    if access:
        return access
    refresh = (fields.get("refresh_token") or "").strip()
    client_id = (fields.get("client_id") or "").strip()
    client_secret = (fields.get("client_secret") or "").strip()
    if not refresh or not client_id or not client_secret:
        return ""
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            return ""
        data = resp.json()
        return (data.get("access_token") or "").strip()


async def _refresh_outlook_access(fields: dict[str, Any]) -> str:
    access = (fields.get("access_token") or "").strip()
    if access:
        return access
    refresh = (fields.get("refresh_token") or "").strip()
    client_id = (fields.get("client_id") or "").strip()
    client_secret = (fields.get("client_secret") or "").strip()
    tenant = (fields.get("tenant_id") or "common").strip() or "common"
    if not refresh or not client_id or not client_secret:
        return ""
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
                "scope": "https://graph.microsoft.com/.default offline_access",
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            return ""
        data = resp.json()
        return (data.get("access_token") or "").strip()


def _build_auth_headers(auth_kind: str, fields: dict[str, Any], bearer: str) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    kind = (auth_kind or "").lower()
    if kind == "shopify":
        token = (fields.get("access_token") or "").strip()
        if token:
            headers["X-Shopify-Access-Token"] = token
        return headers
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    elif kind == "custom":
        token = (fields.get("api_key") or fields.get("token") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


async def prepare_http_request(
    db: Session | None,
    workspace_id: int | None,
    url: str,
    method: str,
    body: str,
    auth_kind: str | None,
    *,
    credential_id: str | None = None,
) -> tuple[str, str, str, dict[str, str]]:
    """Return (url, method, body, headers) with vault auth applied."""
    method = (method or "GET").upper()
    body = body or ""
    auth_ctx = (
        resolve_http_auth(db, workspace_id, auth_kind or "", credential_id=credential_id)
        if auth_kind
        else {"fields": {}, "auth_kind": ""}
    )
    fields = auth_ctx.get("fields") or {}
    kind = str(auth_ctx.get("auth_kind") or "")
    resolved_url = _apply_url_templates(url, fields)

    bearer = ""
    if kind == "youtube":
        api_key = (fields.get("api_key") or "").strip()
        if api_key:
            resolved_url = _append_query_param(resolved_url, "key", api_key)
        else:
            bearer = await _refresh_google_access(fields)
    elif kind in ("google", "google_api"):
        api_key = (fields.get("api_key") or "").strip()
        if api_key and "key=" not in resolved_url:
            resolved_url = _append_query_param(resolved_url, "key", api_key)
        bearer = await _refresh_google_access(fields)
    elif kind == "shopify":
        shop = (fields.get("shop") or "").strip()
        if shop and resolved_url.startswith("https://{{"):
            resolved_url = _apply_url_templates(resolved_url, fields)
        if not resolved_url.startswith("http") and shop:
            resolved_url = f"{shop.rstrip('/')}/{resolved_url.lstrip('/')}"
    elif kind == "outlook":
        bearer = await _refresh_outlook_access(fields)
    elif kind == "custom":
        pass

    headers = _build_auth_headers(kind, fields, bearer)
    safe_url = assert_safe_url(resolved_url)
    return safe_url, method, body, headers


async def fetch_http_authenticated(
    db: Session | None,
    workspace_id: int | None,
    url: str,
    method: str = "GET",
    body: str = "",
    auth_kind: str | None = None,
    *,
    credential_id: str | None = None,
) -> str:
    safe_url, method, body, headers = await prepare_http_request(
        db,
        workspace_id,
        url,
        method,
        body,
        auth_kind,
        credential_id=credential_id,
    )
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if method == "POST":
            content_type = headers.get("Content-Type")
            if body and (body.strip().startswith("{") or body.strip().startswith("[")):
                if not content_type:
                    headers["Content-Type"] = "application/json"
                resp = await client.post(safe_url, content=body, headers=headers)
            else:
                resp = await client.post(safe_url, content=body or None, headers=headers)
        else:
            resp = await client.get(safe_url, headers=headers)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return json.dumps(resp.json())[:8000]
        return (resp.text or "")[:8000]


async def probe_http_auth(
    db: Session,
    workspace_id: int,
    auth_kind: str,
    *,
    credential_id: str | None = None,
) -> dict[str, Any]:
    """Lightweight credential dry-run for sandbox / approve."""
    kind = (auth_kind or "").lower()
    auth_ctx = resolve_http_auth(db, workspace_id, kind, credential_id=credential_id)
    fields = auth_ctx.get("fields") or {}
    if not fields:
        return {"ok": False, "detail": f"No vault credentials for {kind or 'http'}"}

    probe_urls: dict[str, tuple[str, str, str | None]] = {
        "youtube": (
            "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true",
            "GET",
            "youtube",
        ),
        "google": ("https://www.googleapis.com/discovery/v1/apis", "GET", "google"),
        "google_api": ("https://www.googleapis.com/discovery/v1/apis", "GET", "google"),
        "shopify": ("https://{{shop}}/admin/api/2024-01/shop.json", "GET", "shopify"),
        "custom": ("{{base_url}}", "GET", "custom"),
        "outlook": ("https://graph.microsoft.com/v1.0/me", "GET", "outlook"),
    }
    spec = probe_urls.get(kind)
    if not spec:
        return {"ok": True, "detail": f"Credentials present for {kind} (no live probe URL)"}

    url, method, auth = spec
    if kind == "custom":
        base = (fields.get("base_url") or "").strip().rstrip("/")
        if not base:
            return {"ok": False, "detail": "Custom API base_url missing in vault"}
        url = base

    try:
        await fetch_http_authenticated(
            db,
            workspace_id,
            url,
            method,
            "",
            auth,
            credential_id=auth_ctx.get("credential_id"),
        )
        return {"ok": True, "detail": f"{kind} credential probe succeeded"}
    except SafeUrlError as exc:
        return {"ok": False, "detail": str(exc)[:300]}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:300]}
