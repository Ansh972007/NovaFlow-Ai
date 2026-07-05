import csv
import io
from typing import Any


def parse_csv_text(text: str) -> list[dict[str, str]]:
    if not (text or "").strip():
        return []
    reader = csv.DictReader(io.StringIO(text.strip()))
    rows: list[dict[str, str]] = []
    for raw in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        if any(row.values()):
            rows.append(row)
    return rows


def parse_eval_cases_csv(text: str) -> list[dict[str, Any]]:
    cases = []
    for row in parse_csv_text(text):
        inp = row.get("input") or row.get("question") or row.get("prompt") or ""
        if not inp:
            continue
        cases.append(
            {
                "input": inp,
                "expected": row.get("expected") or row.get("answer") or row.get("output") or "",
                "match_type": (row.get("match_type") or row.get("match") or "contains").lower(),
            }
        )
    return cases


def parse_finetune_rows_csv(text: str) -> list[dict[str, str]]:
    rows = []
    for row in parse_csv_text(text):
        user = row.get("user") or row.get("prompt") or row.get("input") or ""
        assistant = row.get("assistant") or row.get("completion") or row.get("output") or ""
        if not user or not assistant:
            continue
        entry: dict[str, str] = {"user": user, "assistant": assistant}
        system = row.get("system") or ""
        if system:
            entry["system"] = system
        rows.append(entry)
    return rows
