from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import EvalRun, EvalSuite, FineTuneDataset, FineTuneJob, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.drift import compute_prompt_drift
from app.services.finetune import job_dict, refresh_finetune_job, start_finetune_job
from app.services.model_lab import (
    create_dataset_from_knowledge,
    dataset_dict_from_row,
    deploy_finetune_to_assistant,
    pipeline_dict,
)

router = APIRouter(tags=["Model Lab"])


@router.get("/model-lab/drift")
def get_prompt_drift(
    suite_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    return ok(compute_prompt_drift(db, ctx.workspace_id, suite_id=suite_id, limit=limit))


@router.post("/model-lab/dataset-from-knowledge")
def dataset_from_knowledge(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    knowledge_ids = body.get("knowledge_ids") or []
    if not isinstance(knowledge_ids, list) or not knowledge_ids:
        return fail(400, "knowledge_ids required")
    name = (body.get("name") or "Knowledge training set").strip()
    try:
        row = create_dataset_from_knowledge(
            db,
            ctx.user.user_id,
            ctx.workspace_id,
            [int(k) for k in knowledge_ids],
            name,
            system_prompt=(body.get("system_prompt") or "").strip(),
        )
        return ok(dataset_dict_from_row(row))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/model-lab/train-and-eval")
async def train_and_eval(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    dataset_id = body.get("dataset_id")
    if not dataset_id:
        return fail(400, "dataset_id required")
    dataset = ctx.fetch(FineTuneDataset, dataset_id)
    if not dataset:
        return fail(404, "Dataset not found")

    auto_eval_suite_id = body.get("auto_eval_suite_id")
    if auto_eval_suite_id:
        suite = ctx.fetch(EvalSuite, int(auto_eval_suite_id))
        if not suite:
            return fail(404, "Eval suite not found")

    try:
        job = await start_finetune_job(
            db,
            dataset,
            ctx.user.user_id,
            ctx.workspace_id,
            body.get("provider_id"),
            (body.get("base_model") or "gpt-4o-mini-2024-07-18").strip(),
            webhook_url=(body.get("webhook_url") or "").strip(),
            auto_eval_suite_id=int(auto_eval_suite_id) if auto_eval_suite_id else None,
        )
        return ok(pipeline_dict(job))
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/model-lab/pipelines")
def list_pipelines(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(FineTuneJob)
        
        .order_by(FineTuneJob.create_time.desc())
        .limit(30)
        .all()
    )
    out = []
    for job in rows:
        eval_run = None
        if job.auto_eval_run_id:
            run = db.get(EvalRun, job.auto_eval_run_id)
            if run:
                from app.services.evaluation import run_dict

                eval_run = run_dict(run)
        out.append(pipeline_dict(job, eval_run))
    return ok(out)


@router.post("/model-lab/jobs/{job_id}/refresh")
async def refresh_pipeline_job(
    job_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    job = ctx.fetch(FineTuneJob, job_id)
    if not job:
        return fail(404, "Job not found")
    job = await refresh_finetune_job(db, job)
    eval_run = None
    if job.auto_eval_run_id:
        run = db.get(EvalRun, job.auto_eval_run_id)
        if run:
            from app.services.evaluation import run_dict

            eval_run = run_dict(run)
    return ok(pipeline_dict(job, eval_run))


@router.post("/model-lab/jobs/{job_id}/deploy-assistant")
def deploy_pipeline_assistant(
    job_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    """Apply fine-tuned model workspace-wide and create a live Chat assistant."""
    job = ctx.fetch(FineTuneJob, job_id)
    if not job:
        return fail(404, "Job not found")
    body = body or {}
    try:
        result = deploy_finetune_to_assistant(
            db,
            job,
            ctx.user.user_id,
            ctx.workspace_id,
            name=(body.get("name") or "").strip(),
            prompt=(body.get("prompt") or "").strip(),
            activate=bool(body.get("activate", True)),
            provider_id=body.get("provider_id"),
            knowledge_ids=body.get("knowledge_ids"),
        )
        return ok(result)
    except ValueError as exc:
        return fail(400, str(exc))
