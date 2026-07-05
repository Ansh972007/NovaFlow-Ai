"""Rough fine-tune cost estimates (OpenAI training token pricing)."""

import json

from app.database import FineTuneDataset
from app.services.finetune import build_jsonl

# USD per 1M training tokens (approximate OpenAI list prices)
PRICE_PER_1M_TOKENS: dict[str, float] = {
    "gpt-4o-mini": 3.0,
    "gpt-4o-mini-2024-07-18": 3.0,
    "gpt-3.5-turbo": 8.0,
    "gpt-3.5-turbo-0125": 8.0,
    "gpt-4o": 25.0,
    "gpt-4o-2024-08-06": 25.0,
}

DEFAULT_EPOCHS = 3
CHARS_PER_TOKEN = 4


def _estimate_tokens_from_rows(rows: list[dict]) -> int:
    total_chars = 0
    for row in rows:
        system = (row.get("system") or "").strip()
        user = (row.get("user") or row.get("prompt") or "").strip()
        assistant = (row.get("assistant") or row.get("completion") or "").strip()
        total_chars += len(system) + len(user) + len(assistant)
    return max(1, total_chars // CHARS_PER_TOKEN)


def _price_for_model(base_model: str) -> float:
    model = (base_model or "").strip()
    if model in PRICE_PER_1M_TOKENS:
        return PRICE_PER_1M_TOKENS[model]
    for key, price in PRICE_PER_1M_TOKENS.items():
        if model.startswith(key):
            return price
    return 3.0


def estimate_finetune_cost(dataset: FineTuneDataset, base_model: str) -> dict:
    try:
        rows = json.loads(dataset.rows_json or "[]")
    except json.JSONDecodeError:
        rows = []

    valid_rows = 0
    for row in rows:
        user = (row.get("user") or row.get("prompt") or "").strip()
        assistant = (row.get("assistant") or row.get("completion") or "").strip()
        if user and assistant:
            valid_rows += 1

    estimated_tokens = _estimate_tokens_from_rows(rows)
    training_tokens = estimated_tokens * DEFAULT_EPOCHS
    price_per_1m = _price_for_model(base_model)
    estimated_cost_usd = round((training_tokens / 1_000_000) * price_per_1m, 4)

    try:
        jsonl_bytes = build_jsonl(rows)
        file_size_kb = round(len(jsonl_bytes) / 1024, 1)
    except ValueError:
        file_size_kb = 0

    return {
        "dataset_id": dataset.id,
        "base_model": base_model or "gpt-4o-mini-2024-07-18",
        "row_count": valid_rows,
        "estimated_tokens_per_epoch": estimated_tokens,
        "assumed_epochs": DEFAULT_EPOCHS,
        "estimated_training_tokens": training_tokens,
        "price_per_1m_tokens_usd": price_per_1m,
        "estimated_cost_usd": estimated_cost_usd,
        "jsonl_size_kb": file_size_kb,
        "disclaimer": "Estimate only; actual cost depends on OpenAI billing and epoch count.",
    }
