"""Parse OpenAPI 3 specs into draft HTTP declarative node definitions."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

MAX_OPS = 24
MAX_SPEC_BYTES = 512_000


def _load_spec(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("OpenAPI spec is empty")
    if len(text) > MAX_SPEC_BYTES:
        raise ValueError("OpenAPI spec too large (max 512KB)")
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON OpenAPI spec: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("OpenAPI root must be an object")
        return data
    # Minimal YAML-ish fallback without PyYAML: lines with key: value at root only
    raise ValueError("Paste OpenAPI as JSON, or upload a JSON export of your spec")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (s[:60] or "operation").strip("_")


def _auth_from_spec(spec: dict[str, Any]) -> str:
    schemes = spec.get("components", {}).get("securitySchemes") or {}
    for name, scheme in schemes.items():
        st = str((scheme or {}).get("type") or "").lower()
        if st == "oauth2":
            return "custom"
        if st == "apiKey":
            return "custom"
        if st == "http" and str(scheme.get("scheme") or "").lower() == "bearer":
            return "bearer"
    return "custom"


def _operations_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    base = str(spec.get("servers", [{}])[0].get("url") or "").strip()
    paths = spec.get("paths") or {}
    ops: list[dict[str, Any]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            m = method.lower()
            if m not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(op, dict):
                continue
            op_id = str(op.get("operationId") or f"{m}_{path}").strip()
            summary = str(op.get("summary") or op.get("description") or op_id).strip()
            full_url = urljoin(base + "/", path.lstrip("/")) if base else path
            ops.append(
                {
                    "operation_id": op_id,
                    "summary": summary[:120],
                    "method": m.upper(),
                    "path": path,
                    "url": full_url,
                }
            )
            if len(ops) >= MAX_OPS:
                return ops
    return ops


def draft_definitions_from_openapi(
    raw_spec: str,
    *,
    auth: str | None = None,
    only_operation_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return node definition payloads (not yet persisted)."""
    spec = _load_spec(raw_spec)
    auth_kind = auth or _auth_from_spec(spec)
    ops = _operations_from_spec(spec)
    if not ops:
        raise ValueError("No HTTP operations found in OpenAPI spec")
    allow = set(only_operation_ids or [])
    out: list[dict[str, Any]] = []
    for op in ops:
        if allow and op["operation_id"] not in allow:
            continue
        slug = _slugify(op["operation_id"])
        display = op["summary"][:80] or slug
        out.append(
            {
                "display_name": display,
                "slug": slug,
                "definition": {
                    "slug": slug,
                    "display_name": display,
                    "runtime": "http_declarative",
                    "category": "api",
                    "tags": ["openapi"],
                    "http": {
                        "url": op["url"],
                        "method": op["method"],
                        "body": "{{output}}" if op["method"] in ("POST", "PUT", "PATCH") else "",
                        "auth": auth_kind,
                        "headers": {},
                    },
                },
            }
        )
    if not out:
        raise ValueError("No matching operations for import filter")
    return out


def summarize_openapi(raw_spec: str) -> dict[str, Any]:
    spec = _load_spec(raw_spec)
    ops = _operations_from_spec(spec)
    title = str(spec.get("info", {}).get("title") or "OpenAPI")
    return {
        "title": title,
        "operation_count": len(ops),
        "operations": [
            {"operation_id": o["operation_id"], "summary": o["summary"], "method": o["method"], "path": o["path"]}
            for o in ops[:MAX_OPS]
        ],
    }
