"""ECP data transformation."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def normalize_record(record: dict, mapping: dict[str, str] | None = None) -> dict[str, Any]:
    mapping = mapping or {}
    if not mapping:
        return dict(record)
    return {dst: record.get(src) for dst, src in mapping.items() if src in record}


def validate_schema(record: dict, required: list[str] | None = None) -> dict[str, Any]:
    required = required or []
    missing = [k for k in required if k not in record or record[k] in (None, "")]
    return {"valid": not missing, "missing": missing}


def mask_fields(record: dict, fields: list[str]) -> dict[str, Any]:
    out = dict(record)
    for f in fields:
        if f in out and out[f]:
            out[f] = "***"
    return out


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
