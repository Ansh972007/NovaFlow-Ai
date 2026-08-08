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
        "webhook_url": job.webhook_url or "",
        "webhook_sent": bool(job.webhook_sent),
        "auto_eval_suite_id": job.auto_eval_suite_id,
        "auto_eval_run_id": job.auto_eval_run_id,
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


def _reject_non_finetune_provider(base_url: str, provider_type: str = "") -> None:
    low = (base_url or "").lower()
    ptype = (provider_type or "").lower()
    if "openrouter" in low or ptype == "openrouter":
        raise ValueError(
            "Fine-tuning requires a native OpenAI API key. OpenRouter does not support model training. "
            "Add OpenAI under Credentials → AI / Models."
        )


def _humanize_finetune_error(exc: Exception) -> str:
    raw = str(exc).strip()
    low = raw.lower()
    if "openrouter" in low or ("404" in raw and "fine_tuning" in low):
        return (
            "OpenRouter cannot train models. Add a native OpenAI API key under Credentials → AI / Models."
        )
    if "401" in raw or "invalid api key" in low or "incorrect api key" in low:
        return "OpenAI rejected the API key. Check your key in Credentials → AI / Models."
    if "no api key" in low:
        return "No API key configured. Add an OpenAI key before training."
    if "dataset needs at least one row" in low:
        return "Dataset is empty. Add at least one training row."
    if len(raw) > 300:
        return raw[:300] + "…"
    return raw or "Training failed"


def _provider_openai_key(db: Session, provider_id: int | None) -> tuple[str, str]:
    if provider_id:
        prov = db.get(LlmProvider, provider_id)
        if not prov:
            raise ValueError("Provider not found")
        if prov.provider_type not in {"openai", "azure_openai", "custom"}:
            raise ValueError("Fine-tuning requires an OpenAI-compatible provider")
        if prov.provider_type == "openrouter":
            raise ValueError(
                "Fine-tuning requires a native OpenAI API key. OpenRouter does not support model training."
            )
        key = resolve_api_key(prov)
        base = (prov.base_url or "https://api.openai.com/v1").rstrip("/")
        _reject_non_finetune_provider(base, prov.provider_type or "")
        if not key:
            raise ValueError("Provider API key not configured")
        return key, base

    from app.services.workspace_settings import get_active_config

    cfg = get_active_config(db)
    if cfg.get("provider_type") == "anthropic":
        raise ValueError("Fine-tuning is not supported for Anthropic providers")
    base = (cfg.get("base_url") or "").rstrip("/")
    _reject_non_finetune_provider(base, cfg.get("provider_type") or "")
    if not cfg.get("api_key"):
        raise ValueError("No API key configured for fine-tuning. Add OpenAI under Credentials → AI / Models.")
    return cfg["api_key"], base


async def start_finetune_job(
    db: Session,
    dataset: FineTuneDataset,
    user_id: int,
    workspace_id: int,
    provider_id: int | None,
    base_model: str,
    webhook_url: str = "",
    auto_eval_suite_id: int | None = None,
) -> FineTuneJob:
    from app.services.ab_routing import check_finetune_quota

    check_finetune_quota(db, workspace_id)
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
        webhook_url=(webhook_url or "").strip()[:500],
        webhook_sent=0,
        auto_eval_suite_id=auto_eval_suite_id,
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
        job.error_message = _humanize_finetune_error(exc)
        job.update_time = datetime.utcnow()
        db.commit()

    db.refresh(job)
    return job


async def refresh_finetune_job(db: Session, job: FineTuneJob) -> FineTuneJob:
    if not job.job_id:
        return job
    prev_status = job.status
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
    if job.status != prev_status:
        await send_finetune_webhook_if_needed(db, job)
        if job.status in {"succeeded", "completed"} and job.auto_eval_suite_id and not job.auto_eval_run_id:
            await run_auto_eval_for_job(db, job)
    return job


async def run_auto_eval_for_job(db: Session, job: FineTuneJob) -> None:
    from app.database import EvalSuite
    from app.services.evaluation import run_dict, run_eval_suite

    suite = db.get(EvalSuite, job.auto_eval_suite_id)
    if not suite or suite.workspace_id != job.workspace_id:
        return
    try:
        run = await run_eval_suite(
            db,
            suite,
            job.user_id,
            job.workspace_id or 0,
            assistant_id=suite.assistant_id,
        )
        job.auto_eval_run_id = run.id
        job.update_time = datetime.utcnow()
        db.commit()
        if job.webhook_url and not job.webhook_sent:
            from app.services.webhooks import post_webhook

            await post_webhook(
                job.webhook_url,
                {
                    "event": "finetune_auto_eval",
                    "job": job_dict(job),
                    "eval_run": run_dict(run),
                },
            )
    except Exception:
        pass


TERMINAL_FINETUNE = {"succeeded", "failed", "cancelled", "completed"}


async def send_finetune_webhook_if_needed(db: Session, job: FineTuneJob) -> None:
    if not (job.webhook_url or "").strip():
        return
    if job.webhook_sent:
        return
    if job.status not in TERMINAL_FINETUNE:
        return
    from app.services.webhooks import post_webhook

    await post_webhook(
        job.webhook_url,
        {
            "job_id": job.id,
            "openai_job_id": job.job_id,
            "status": job.status,
            "fine_tuned_model": job.fine_tuned_model or "",
            "error_message": job.error_message or "",
            "dataset_id": job.dataset_id,
        },
        event="finetune.completed",
    )
    job.webhook_sent = 1
    job.update_time = datetime.utcnow()
    db.commit()
    db.refresh(job)


def apply_finetuned_model(
    db: Session,
    job: FineTuneJob,
    *,
    provider_id: int | None = None,
    activate: bool = True,
) -> dict:
    from app.services.llm_providers import activate_provider, get_active_provider_row, provider_dict, update_provider

    model_id = (job.fine_tuned_model or "").strip()
    if not model_id:
        raise ValueError("Job has no fine-tuned model yet — refresh status first")
    if job.status not in {"succeeded", "completed"}:
        raise ValueError(f"Job status is '{job.status}'; wait until training succeeds")

    target_id = provider_id or job.provider_id
    if not target_id:
        active = get_active_provider_row(db)
        if not active:
            raise ValueError("No provider configured — specify provider_id")
        target_id = active.id

    update_provider(db, target_id, {"chat_model": model_id})
    if activate:
        return activate_provider(db, target_id)
    prov = db.get(LlmProvider, target_id)
    return provider_dict(prov)
