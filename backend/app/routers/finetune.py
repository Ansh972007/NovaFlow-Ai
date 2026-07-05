from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import FineTuneDataset, FineTuneJob, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.finetune import dataset_dict, job_dict, refresh_finetune_job, start_finetune_job

router = APIRouter(tags=["Fine-tune"])


@router.get("/finetune/datasets")
def list_datasets(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(FineTuneDataset)
        .filter(FineTuneDataset.workspace_id == ctx.workspace_id)
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


@router.get("/finetune/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    row = db.get(FineTuneDataset, dataset_id)
    if not row or row.workspace_id != ctx.workspace_id:
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

    row = db.get(FineTuneDataset, dataset_id)
    if not row or row.workspace_id != ctx.workspace_id:
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
    row = db.get(FineTuneDataset, dataset_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Dataset not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": dataset_id})


@router.get("/finetune/jobs")
def list_jobs(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(FineTuneJob)
        .filter(FineTuneJob.workspace_id == ctx.workspace_id)
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
    dataset = db.get(FineTuneDataset, dataset_id)
    if not dataset or dataset.workspace_id != ctx.workspace_id:
        return fail(404, "Dataset not found")
    try:
        job = await start_finetune_job(
            db,
            dataset,
            ctx.user.user_id,
            ctx.workspace_id,
            body.get("provider_id"),
            (body.get("base_model") or "gpt-4o-mini-2024-07-18").strip(),
        )
        return ok(job_dict(job))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/finetune/jobs/{job_id}/refresh")
async def refresh_job(job_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    job = db.get(FineTuneJob, job_id)
    if not job or job.workspace_id != ctx.workspace_id:
        return fail(404, "Job not found")
    try:
        job = await refresh_finetune_job(db, job)
        return ok(job_dict(job))
    except ValueError as exc:
        return fail(400, str(exc))
