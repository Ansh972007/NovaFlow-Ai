from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import AbModelRoute, FineTuneDataset, FineTuneJob, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.csv_import import parse_finetune_rows_csv
from app.services.finetune import (
    apply_finetuned_model,
    dataset_dict,
    job_dict,
    refresh_finetune_job,
    start_finetune_job,
)
from app.services.finetune_cost import estimate_finetune_cost
from app.services.ab_routing import route_dict

router = APIRouter(tags=["Fine-tune"])


@router.get("/finetune/datasets")
def list_datasets(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(FineTuneDataset)
        
        .order_by(FineTuneDataset.update_time.desc())
        .all()
    )
    return ok([dataset_dict(r) for r in rows])


@router.post("/finetune/datasets")
def create_dataset(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    import json

    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "Name required")
    rows = body.get("rows") or []
    row = FineTuneDataset(
        name=name[:120],
        description=(body.get("description") or "").strip()[:500],
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        rows_json=json.dumps(rows),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(dataset_dict(row))


@router.get("/finetune/datasets/{dataset_id}/estimate")
def estimate_dataset_cost(
    dataset_id: int,
    base_model: str = "gpt-4o-mini-2024-07-18",
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    row = ctx.fetch(FineTuneDataset, dataset_id)
    if not row:
        return fail(404, "Dataset not found")
    return ok(estimate_finetune_cost(row, base_model.strip()))


@router.get("/finetune/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    row = ctx.fetch(FineTuneDataset, dataset_id)
    if not row:
        return fail(404, "Dataset not found")
    return ok(dataset_dict(row))


@router.patch("/finetune/datasets/{dataset_id}")
def update_dataset(
    dataset_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    import json

    row = ctx.fetch(FineTuneDataset, dataset_id)
    if not row:
        return fail(404, "Dataset not found")
    if "name" in body and body["name"]:
        row.name = str(body["name"]).strip()[:120]
    if "description" in body:
        row.description = str(body["description"] or "").strip()[:500]
    if "rows" in body and isinstance(body["rows"], list):
        row.rows_json = json.dumps(body["rows"])
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok(dataset_dict(row))


@router.delete("/finetune/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    row = ctx.fetch(FineTuneDataset, dataset_id)
    if not row:
        return fail(404, "Dataset not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": dataset_id})


@router.get("/finetune/jobs")
def list_jobs(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(FineTuneJob)
        
        .order_by(FineTuneJob.create_time.desc())
        .limit(50)
        .all()
    )
    return ok([job_dict(j) for j in rows])


@router.post("/finetune/jobs")
async def create_job(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    dataset_id = body.get("dataset_id")
    if not dataset_id:
        return fail(400, "dataset_id required")
    dataset = ctx.fetch(FineTuneDataset, dataset_id)
    if not dataset:
        return fail(404, "Dataset not found")
    try:
        job = await start_finetune_job(
            db,
            dataset,
            ctx.user.user_id,
            ctx.workspace_id,
            body.get("provider_id"),
            (body.get("base_model") or "gpt-4o-mini-2024-07-18").strip(),
            webhook_url=(body.get("webhook_url") or "").strip(),
            auto_eval_suite_id=int(body["auto_eval_suite_id"]) if body.get("auto_eval_suite_id") else None,
        )
        return ok(job_dict(job))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/finetune/datasets/{dataset_id}/import-csv")
async def import_dataset_csv(
    dataset_id: int,
    body: dict | None = None,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    import json

    row = ctx.fetch(FineTuneDataset, dataset_id)
    if not row:
        return fail(404, "Dataset not found")

    text = ""
    if file and file.filename:
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="replace")
    elif body and body.get("csv"):
        text = str(body["csv"])
    else:
        return fail(400, "Provide csv text or upload a .csv file")

    parsed = parse_finetune_rows_csv(text)
    if not parsed:
        return fail(400, "No valid rows. Columns: user, assistant (optional: system)")

    try:
        existing = json.loads(row.rows_json or "[]")
    except json.JSONDecodeError:
        existing = []
    existing.extend(parsed)
    row.rows_json = json.dumps(existing)
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok({"imported": len(parsed), "dataset": dataset_dict(row)})


@router.post("/finetune/jobs/{job_id}/apply")
def apply_job(
    job_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    job = ctx.fetch(FineTuneJob, job_id)
    if not job:
        return fail(404, "Job not found")
    opts = body or {}
    try:
        provider = apply_finetuned_model(
            db,
            job,
            provider_id=opts.get("provider_id"),
            activate=bool(opts.get("activate", True)),
        )
        return ok({"provider": provider, "job": job_dict(job)})
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/finetune/jobs/{job_id}/refresh")
async def refresh_job(job_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    job = ctx.fetch(FineTuneJob, job_id)
    if not job:
        return fail(404, "Job not found")
    try:
        job = await refresh_finetune_job(db, job)
        return ok(job_dict(job))
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/finetune/ab-routes")
def list_ab_routes(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(AbModelRoute)
        
        .order_by(AbModelRoute.update_time.desc())
        .all()
    )
    return ok([route_dict(r) for r in rows])


@router.post("/finetune/ab-routes")
def create_ab_route(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    base = (body.get("base_model") or "").strip()
    variant = (body.get("variant_model") or "").strip()
    if not base or not variant:
        return fail(400, "base_model and variant_model required")
    row = AbModelRoute(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        provider_id=body.get("provider_id"),
        base_model=base,
        variant_model=variant,
        variant_traffic_pct=max(0, min(100, int(body.get("variant_traffic_pct") or 50))),
        enabled=1 if body.get("enabled", True) else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(route_dict(row))


@router.patch("/finetune/ab-routes/{route_id}")
def update_ab_route(
    route_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = ctx.fetch(AbModelRoute, route_id)
    if not row:
        return fail(404, "Route not found")
    if "base_model" in body and body["base_model"]:
        row.base_model = str(body["base_model"]).strip()
    if "variant_model" in body and body["variant_model"]:
        row.variant_model = str(body["variant_model"]).strip()
    if "variant_traffic_pct" in body:
        row.variant_traffic_pct = max(0, min(100, int(body["variant_traffic_pct"])))
    if "enabled" in body:
        row.enabled = 1 if body["enabled"] else 0
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok(route_dict(row))


@router.delete("/finetune/ab-routes/{route_id}")
def delete_ab_route(route_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    row = ctx.fetch(AbModelRoute, route_id)
    if not row:
        return fail(404, "Route not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": route_id})
