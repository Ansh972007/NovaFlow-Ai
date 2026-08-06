"""Runtime execution for declarative API nodes from the node library."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.database import NodeDefinition
from app.security.ssrf import SafeUrlError
from app.services.workflow_http_auth import prepare_http_request


def _apply_template(template: str, context: dict) -> str:
    from app.services.workflow import _apply_template as wf_apply

    return wf_apply(template or "", context)


def _json_path_get(data: Any, path: str) -> Any:
    if not path or path == ".":
        return data
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return None
    return cur


def apply_output_mapping(raw_text: str, mapping: dict[str, Any] | None, context: dict) -> str:
    mapping = mapping or {}
    template = mapping.get("template") or "{{json}}"
    path = (mapping.get("path") or "").strip()
    parsed: Any = None
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = raw_text
    if path and parsed is not None:
        extracted = _json_path_get(parsed, path)
        if extracted is not None:
            if isinstance(extracted, (dict, list)):
                context["json"] = json.dumps(extracted, ensure_ascii=False)[:8000]
            else:
                context["json"] = str(extracted)[:8000]
    else:
        if isinstance(parsed, (dict, list)):
            context["json"] = json.dumps(parsed, ensure_ascii=False)[:8000]
        else:
            context["json"] = str(parsed or raw_text)[:8000]
    out = _apply_template(template, context)
    return out[:8000]


def merge_input_schema(context: dict, data: dict, input_schema: dict | None) -> dict:
    merged = dict(context)
    fields = (input_schema or {}).get("fields") or []
    for field in fields:
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        if key in data and data[key] is not None:
            merged[key] = data[key]
        elif field.get("default") is not None:
            merged[key] = field.get("default")
    return merged


def definition_from_row(row: NodeDefinition) -> dict[str, Any]:
    try:
        return json.loads(row.definition_json or "{}")
    except json.JSONDecodeError:
        return {}


async def execute_http_probe(
    db: Session,
    workspace_id: int,
    http_cfg: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dry-run HTTP request for probe/test without persisting."""
    ctx = dict(context or {})
    ctx.setdefault("input", ctx.get("input") or "probe")
    ctx.setdefault("output", ctx.get("output") or "")
    url = _apply_template(str(http_cfg.get("url") or ""), ctx).strip()
    method = str(http_cfg.get("method") or "GET").upper()
    body = _apply_template(str(http_cfg.get("body") or ""), ctx)
    auth_kind = (http_cfg.get("auth") or "").strip() or None
    credential_id = (http_cfg.get("credential_id") or "").strip() or None
    extra_headers = dict(http_cfg.get("headers") or {})

    if not url:
        return {"ok": False, "error": "URL is required", "status_code": 0, "body_preview": ""}

    try:
        safe_url, method, body, headers = await prepare_http_request(
            db,
            workspace_id,
            url,
            method,
            body,
            auth_kind,
            credential_id=credential_id,
        )
        for k, v in extra_headers.items():
            headers[str(k)] = _apply_template(str(v), ctx)
        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if method == "POST":
                if body and (body.strip().startswith("{") or body.strip().startswith("[")):
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    resp = await client.post(safe_url, content=body, headers=headers)
                else:
                    resp = await client.post(safe_url, content=body or None, headers=headers)
            else:
                resp = await client.get(safe_url, headers=headers)
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            try:
                preview = json.dumps(resp.json(), ensure_ascii=False)[:2000]
            except Exception:
                preview = (resp.text or "")[:2000]
        else:
            preview = (resp.text or "")[:2000]
        ok = resp.status_code < 400
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "body_preview": preview,
            "url": safe_url,
            "error": "" if ok else f"HTTP {resp.status_code}",
        }
    except SafeUrlError as exc:
        return {"ok": False, "error": str(exc), "status_code": 0, "body_preview": ""}
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "status_code": exc.response.status_code,
            "body_preview": (exc.response.text or "")[:2000],
            "error": str(exc),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "status_code": 0, "body_preview": ""}


async def execute_api_node_definition(
    db: Session,
    workspace_id: int | None,
    data: dict[str, Any],
    context: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Load published node definition and execute its HTTP config."""
    node_def_id = str(data.get("node_def_id") or "").strip()
    if not node_def_id:
        raise ValueError("api_node missing node_def_id")
    row = db.get(NodeDefinition, node_def_id)
    if not row or (workspace_id and row.workspace_id != workspace_id):
        raise ValueError("Node definition not found")
    if row.status != "published":
        raise ValueError(f"Node definition '{row.slug}' is not published")

    defn = definition_from_row(row)
    runtime = (defn.get("runtime") or "http_declarative").strip()
    if runtime != "http_declarative":
        raise ValueError(f"Unsupported runtime: {runtime}")

    http_cfg = dict(defn.get("http") or {})
    if data.get("credential_id"):
        http_cfg["credential_id"] = data.get("credential_id")
    merged_ctx = merge_input_schema(context, data, defn.get("input_schema"))
    probe = await execute_http_probe(db, row.workspace_id, http_cfg, merged_ctx)
    if not probe.get("ok"):
        raise ValueError(probe.get("error") or "API node request failed")

    raw = probe.get("body_preview") or ""
    mapped = apply_output_mapping(raw, defn.get("output_mapping"), merged_ctx)
    return mapped, probe


def normalize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "_", (raw or "").lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if len(slug) < 2:
        slug = f"api_{slug or 'node'}"
    return slug[:80]
