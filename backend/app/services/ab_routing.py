import random
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import AbModelRoute, EvalRun, FineTuneJob


def route_dict(row: AbModelRoute) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "provider_id": row.provider_id,
        "base_model": row.base_model or "",
        "variant_model": row.variant_model or "",
        "variant_traffic_pct": row.variant_traffic_pct or 50,
        "enabled": bool(row.enabled),
        "create_time": row.create_time.isoformat() if row.create_time else None,
    }


def pick_ab_model(db: Session, workspace_id: int, default_model: str) -> dict | None:
    row = (
        db.query(AbModelRoute)
        .filter(AbModelRoute.workspace_id == workspace_id, AbModelRoute.enabled == 1)
        .order_by(AbModelRoute.update_time.desc())
        .first()
    )
    if not row or not row.variant_model:
        return None
    base = (row.base_model or default_model or "").strip()
    variant = row.variant_model.strip()
    pct = max(0, min(100, row.variant_traffic_pct or 50))
    use_variant = random.randint(1, 100) <= pct
    return {
        "model": variant if use_variant else base,
        "variant": "variant" if use_variant else "base",
        "route_id": row.id,
    }


def quota_dict(row) -> dict:
    return {
        "workspace_id": row.workspace_id,
        "eval_runs_monthly_limit": row.eval_runs_monthly_limit or 0,
        "finetune_jobs_monthly_limit": row.finetune_jobs_monthly_limit or 0,
        "eval_runs_this_month": row.eval_runs_this_month if hasattr(row, "eval_runs_this_month") else None,
        "finetune_jobs_this_month": row.finetune_jobs_this_month if hasattr(row, "finetune_jobs_this_month") else None,
    }


def _month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def count_eval_runs_month(db: Session, workspace_id: int) -> int:
    return (
        db.query(EvalRun)
        .filter(EvalRun.workspace_id == workspace_id, EvalRun.create_time >= _month_start())
        .count()
    )


def count_finetune_jobs_month(db: Session, workspace_id: int) -> int:
    return (
        db.query(FineTuneJob)
        .filter(FineTuneJob.workspace_id == workspace_id, FineTuneJob.create_time >= _month_start())
        .count()
    )


def check_eval_quota(db: Session, workspace_id: int) -> None:
    from app.database import WorkspaceQuota

    q = db.get(WorkspaceQuota, workspace_id)
    if not q or not q.eval_runs_monthly_limit:
        return
    used = count_eval_runs_month(db, workspace_id)
    if used >= q.eval_runs_monthly_limit:
        raise ValueError(
            f"Monthly eval run quota reached ({used}/{q.eval_runs_monthly_limit}). "
            "Contact workspace admin to raise limits."
        )


def check_finetune_quota(db: Session, workspace_id: int) -> None:
    from app.database import WorkspaceQuota

    q = db.get(WorkspaceQuota, workspace_id)
    if not q or not q.finetune_jobs_monthly_limit:
        return
    used = count_finetune_jobs_month(db, workspace_id)
    if used >= q.finetune_jobs_monthly_limit:
        raise ValueError(
            f"Monthly fine-tune job quota reached ({used}/{q.finetune_jobs_monthly_limit}). "
            "Contact workspace admin to raise limits."
        )


def quotas_with_usage(db: Session, workspace_id: int) -> dict:
    from app.database import WorkspaceQuota

    q = db.get(WorkspaceQuota, workspace_id)
    if not q:
        q = WorkspaceQuota(workspace_id=workspace_id)
        db.add(q)
        db.commit()
        db.refresh(q)
    data = quota_dict(q)
    data["eval_runs_this_month"] = count_eval_runs_month(db, workspace_id)
    data["finetune_jobs_this_month"] = count_finetune_jobs_month(db, workspace_id)
    return data
