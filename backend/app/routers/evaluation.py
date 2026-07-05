from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import Assistant, EvalCase, EvalComparison, EvalRun, EvalSchedule, EvalSuite, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.csv_import import parse_eval_cases_csv
from app.services.evaluation import (
    case_dict,
    comparison_dict,
    run_dict,
    run_eval_comparison,
    run_eval_suite,
    schedule_dict,
    suite_dict,
)

router = APIRouter(tags=["Evaluation"])


@router.get("/eval/suites")
def list_suites(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(EvalSuite)
        .filter(EvalSuite.workspace_id == ctx.workspace_id)
        .order_by(EvalSuite.update_time.desc())
        .all()
    )
    return ok([suite_dict(s) for s in rows])


@router.post("/eval/suites")
def create_suite(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    assistant_id = (body.get("assistant_id") or "").strip()
    if not name or not assistant_id:
        return fail(400, "Name and assistant_id required")
    assistant = db.get(Assistant, assistant_id)
    if not assistant or assistant.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")

    suite = EvalSuite(
        name=name[:120],
        description=(body.get("description") or "").strip()[:500],
        assistant_id=assistant_id,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
    )
    db.add(suite)
    db.flush()

    for i, row in enumerate(body.get("cases") or []):
        inp = (row.get("input") or row.get("question") or "").strip()
        if not inp:
            continue
        db.add(
            EvalCase(
                suite_id=suite.id,
                input_text=inp,
                expected_text=(row.get("expected") or row.get("answer") or "").strip(),
                match_type=(row.get("match_type") or "contains").strip().lower(),
                sort_order=i,
            )
        )

    db.commit()
    db.refresh(suite)
    return ok(suite_dict(suite))


@router.get("/eval/suites/{suite_id}")
def get_suite(suite_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    data = suite_dict(suite)
    data["cases"] = [case_dict(c) for c in suite.cases]
    runs = (
        db.query(EvalRun)
        .filter(EvalRun.suite_id == suite_id)
        .order_by(EvalRun.create_time.desc())
        .limit(10)
        .all()
    )
    data["recent_runs"] = [run_dict(r) for r in runs]
    return ok(data)


@router.delete("/eval/suites/{suite_id}")
def delete_suite(suite_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    db.delete(suite)
    db.commit()
    return ok({"deleted": suite_id})


@router.post("/eval/suites/{suite_id}/cases")
def add_case(suite_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    inp = (body.get("input") or "").strip()
    if not inp:
        return fail(400, "Input required")
    case = EvalCase(
        suite_id=suite_id,
        input_text=inp,
        expected_text=(body.get("expected") or "").strip(),
        match_type=(body.get("match_type") or "contains").strip().lower(),
        sort_order=body.get("sort_order") or len(suite.cases),
    )
    db.add(case)
    suite.update_time = datetime.utcnow()
    db.commit()
    db.refresh(case)
    return ok(case_dict(case))


@router.delete("/eval/suites/{suite_id}/cases/{case_id}")
def delete_case(
    suite_id: int,
    case_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    case = db.get(EvalCase, case_id)
    if not case or case.suite_id != suite_id:
        return fail(404, "Case not found")
    db.delete(case)
    suite.update_time = datetime.utcnow()
    db.commit()
    return ok({"deleted": case_id})


@router.post("/eval/suites/{suite_id}/import-csv")
async def import_cases_csv(
    suite_id: int,
    body: dict | None = None,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")

    text = ""
    if file and file.filename:
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="replace")
    elif body and body.get("csv"):
        text = str(body["csv"])
    else:
        return fail(400, "Provide csv text or upload a .csv file")

    parsed = parse_eval_cases_csv(text)
    if not parsed:
        return fail(400, "No valid rows found. Columns: input, expected, match_type")

    start_order = len(suite.cases)
    for i, row in enumerate(parsed):
        db.add(
            EvalCase(
                suite_id=suite_id,
                input_text=row["input"],
                expected_text=row.get("expected") or "",
                match_type=row.get("match_type") or "contains",
                sort_order=start_order + i,
            )
        )
    suite.update_time = datetime.utcnow()
    db.commit()
    db.refresh(suite)
    return ok({"imported": len(parsed), "suite": suite_dict(suite)})


@router.post("/eval/suites/{suite_id}/run")
async def run_suite(
    suite_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    if not suite.cases:
        return fail(400, "Add at least one test case before running")
    opts = body or {}
    scoring = (opts.get("scoring") or "rules").strip().lower()
    threshold = int(opts.get("judge_threshold") or 4)
    try:
        run = await run_eval_suite(
            db,
            suite,
            ctx.user.user_id,
            ctx.workspace_id,
            scoring=scoring,
            judge_threshold=threshold,
            webhook_url=(opts.get("webhook_url") or "").strip(),
        )
        return ok(run_dict(run))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/eval/suites/{suite_id}/compare")
async def compare_suite(
    suite_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    assistant_ids = body.get("assistant_ids") or []
    if not isinstance(assistant_ids, list):
        return fail(400, "assistant_ids must be a list")
    scoring = (body.get("scoring") or "rules").strip().lower()
    threshold = int(body.get("judge_threshold") or 4)
    try:
        comparison = await run_eval_comparison(
            db,
            suite,
            [str(a).strip() for a in assistant_ids if str(a).strip()],
            ctx.user.user_id,
            ctx.workspace_id,
            scoring=scoring,
            judge_threshold=threshold,
        )
        return ok(comparison_dict(comparison))
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/eval/comparisons")
def list_comparisons(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(EvalComparison)
        .filter(EvalComparison.workspace_id == ctx.workspace_id)
        .order_by(EvalComparison.create_time.desc())
        .limit(20)
        .all()
    )
    return ok([comparison_dict(r) for r in rows])


@router.get("/eval/comparisons/{comparison_id}")
def get_comparison(comparison_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    row = db.get(EvalComparison, comparison_id)
    if not row or row.workspace_id != ctx.workspace_id:
        return fail(404, "Comparison not found")
    return ok(comparison_dict(row))


@router.get("/eval/schedules")
def list_schedules(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        db.query(EvalSchedule)
        .filter(EvalSchedule.workspace_id == ctx.workspace_id)
        .order_by(EvalSchedule.update_time.desc())
        .all()
    )
    return ok([schedule_dict(r) for r in rows])


@router.post("/eval/schedules")
def create_schedule(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite_id = body.get("suite_id")
    if not suite_id:
        return fail(400, "suite_id required")
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    interval = max(1, int(body.get("interval_hours") or 24))
    now = datetime.utcnow()
    sched = EvalSchedule(
        suite_id=suite_id,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        interval_hours=interval,
        enabled=1 if body.get("enabled", True) else 0,
        scoring=(body.get("scoring") or "rules").strip().lower(),
        judge_threshold=int(body.get("judge_threshold") or 4),
        webhook_url=(body.get("webhook_url") or "").strip()[:500],
        next_run_at=now + timedelta(hours=interval),
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return ok(schedule_dict(sched))


@router.patch("/eval/schedules/{schedule_id}")
def update_schedule(
    schedule_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    sched = db.get(EvalSchedule, schedule_id)
    if not sched or sched.workspace_id != ctx.workspace_id:
        return fail(404, "Schedule not found")
    if "enabled" in body:
        sched.enabled = 1 if body["enabled"] else 0
    if "interval_hours" in body:
        sched.interval_hours = max(1, int(body["interval_hours"]))
    if "scoring" in body:
        sched.scoring = str(body["scoring"]).strip().lower()
    if "judge_threshold" in body:
        sched.judge_threshold = int(body["judge_threshold"])
    if "webhook_url" in body:
        sched.webhook_url = str(body["webhook_url"] or "").strip()[:500]
    sched.update_time = datetime.utcnow()
    db.commit()
    db.refresh(sched)
    return ok(schedule_dict(sched))


@router.delete("/eval/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    sched = db.get(EvalSchedule, schedule_id)
    if not sched or sched.workspace_id != ctx.workspace_id:
        return fail(404, "Schedule not found")
    db.delete(sched)
    db.commit()
    return ok({"deleted": schedule_id})


@router.post("/eval/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    sched = db.get(EvalSchedule, schedule_id)
    if not sched or sched.workspace_id != ctx.workspace_id:
        return fail(404, "Schedule not found")
    suite = db.get(EvalSuite, sched.suite_id)
    if not suite:
        return fail(404, "Suite not found")
    try:
        run = await run_eval_suite(
            db,
            suite,
            ctx.user.user_id,
            ctx.workspace_id,
            scoring=sched.scoring or "rules",
            judge_threshold=sched.judge_threshold or 4,
            webhook_url=sched.webhook_url or "",
        )
        now = datetime.utcnow()
        sched.last_run_at = now
        sched.next_run_at = now + timedelta(hours=max(1, sched.interval_hours or 24))
        sched.update_time = now
        db.commit()
        return ok({"run": run_dict(run), "schedule": schedule_dict(sched)})
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/eval/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    run = db.get(EvalRun, run_id)
    if not run or run.workspace_id != ctx.workspace_id:
        return fail(404, "Run not found")
    return ok(run_dict(run))
