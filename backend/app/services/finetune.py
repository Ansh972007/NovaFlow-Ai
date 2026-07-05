import io
import json
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.database import FineTuneDataset, FineTuneJob, LlmProvider
from app.services.llm_providers import resolve_api_key


def dataset_dict(row: FineTuneDataset) -> dict:
    try:
        rows = json.loads(row.rows_json or "[]")
    except json.JSONDecodeError:
        rows = []
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "row_count": len(rows),
        "rows": rows,
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "update_time": row.update_time.isoformat() if row.update_time else None,
    }


def job_dict(job: FineTuneJob) -> dict:
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "provider_id": job.provider_id,
        "base_model": job.base_model,
        "status": job.status,
        "openai_file_id": job.openai_file_id or "",
        "job_id": job.job_id or "",
        "fine_tuned_model": job.fine_tuned_model or "",
        "error_message": job.error_message or "",
        "create_time": job.create_time.isoformat() if job.create_time else None,
        "update_time": job.update_time.isoformat() if job.update_time else None,
    }


def _openai_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def build_jsonl(rows: list[dict]) -> bytes:
    lines = []
    for row in rows:
        system = (row.get("system") or "").strip()
        user = (row.get("user") or row.get("prompt") or "").strip()
        assistant = (row.get("assistant") or row.get("completion") or "").strip()
        if not user or not assistant:
            continue
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})
        lines.append(json.dumps({"messages": messages}))
    if not lines:
        raise ValueError("Dataset needs at least one row with user + assistant text")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _provider_openai_key(db: Session, provider_id: int | None) -> tuple[str, str]:
    if provider_id:
        prov = db.get(LlmProvider, provider_id)
        if not prov:
            raise ValueError("Provider not found")
        if prov.provider_type not in {"openai", "azure_openai", "custom"}:
            raise ValueError("Fine-tuning requires an OpenAI-compatible provider")
        key = resolve_api_key(prov)
        base = (prov.base_url or "https://api.openai.com/v1").rstrip("/")
        if not key:
            raise ValueError("Provider API key not configured")
        return key, base

    from app.services.workspace_settings import get_active_config

    cfg = get_active_config(db)
    if cfg.get("provider_type") == "anthropic":
        raise ValueError("Fine-tuning is not supported for Anthropic providers")
    if not cfg.get("api_key"):
        raise ValueError("No API key configured for fine-tuning")
    return cfg["api_key"], cfg["base_url"].rstrip("/")


async def start_finetune_job(
    db: Session,
    dataset: FineTuneDataset,
    user_id: int,
    workspace_id: int,
    provider_id: int | None,
    base_model: str,
) -> FineTuneJob:
    rows = json.loads(dataset.rows_json or "[]")
    content = build_jsonl(rows)
    api_key, base_url = _provider_openai_key(db, provider_id)

    job = FineTuneJob(
        dataset_id=dataset.id,
        user_id=user_id,
        workspace_id=workspace_id,
        provider_id=provider_id,
        base_model=base_model or "gpt-4o-mini-2024-07-18",
        status="uploading",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            files = {"file": ("training.jsonl", io.BytesIO(content), "application/jsonl")}
            data = {"purpose": "fine-tune"}
            upload = await client.post(
                f"{base_url}/files",
                headers=_openai_headers(api_key),
                files=files,
                data=data,
            )
            upload.raise_for_status()
            file_id = upload.json()["id"]
            job.openai_file_id = file_id
            job.status = "queued"
            db.commit()

            create = await client.post(
                f"{base_url}/fine_tuning/jobs",
                headers={**_openai_headers(api_key), "Content-Type": "application/json"},
                json={"training_file": file_id, "model": job.base_model},
            )
            create.raise_for_status()
            payload = create.json()
            job.job_id = payload.get("id") or ""
            job.status = payload.get("status") or "queued"
            job.fine_tuned_model = payload.get("fine_tuned_model") or ""
            job.update_time = datetime.utcnow()
            db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        job.update_time = datetime.utcnow()
        db.commit()

    db.refresh(job)
    return job


async def refresh_finetune_job(db: Session, job: FineTuneJob) -> FineTuneJob:
    if not job.job_id:
        return job
    api_key, base_url = _provider_openai_key(db, job.provider_id)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"{base_url}/fine_tuning/jobs/{job.job_id}",
            headers=_openai_headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()
    job.status = data.get("status") or job.status
    job.fine_tuned_model = data.get("fine_tuned_model") or job.fine_tuned_model or ""
    if data.get("error"):
        err = data["error"]
        job.error_message = err.get("message") if isinstance(err, dict) else str(err)
    job.update_time = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job
