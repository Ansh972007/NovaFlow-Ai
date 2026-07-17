from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import (
    Assistant,
    EvalCase,
    EvalComparison,
    EvalRegressionAlert,
    EvalRun,
    EvalSchedule,
    EvalSuite,
    get_db,
)
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.csv_import import parse_eval_cases_csv
from app.services.eval_alerts import alert_dict, comparison_trends, suite_trends
from app.services.eval_diff import diff_eval_runs
from app.services.cron_schedule import validate_cron
from app.services.eval_templates import get_template, list_templates
from app.services.evaluation import (
    case_dict,
    comparison_dict,
    compute_schedule_next_run,
    run_dict,
    run_eval_comparison,
    run_eval_suite,
    schedule_dict,
    suite_dict,
)

router = APIRouter(tags=["Evaluation"])


@router.get("/eval/templates")
def get_eval_templates():
    return ok(list_templates())


@router.post("/eval/suites/from-template")
def create_suite_from_template(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    template_id = (body.get("template_id") or "").strip()
    assistant_id = (body.get("assistant_id") or "").strip()
    if not template_id or not assistant_id:
        return fail(400, "template_id and assistant_id required")
    tpl = get_template(template_id)
    if not tpl:
        return fail(404, "Template not found")
    assistant = ctx.fetch(Assistant, assistant_id)
    if not assistant:
        return fail(404, "Assistant not found")

    name = (body.get("name") or tpl["name"]).strip()[:120]
    suite = EvalSuite(
        name=name,
        description=tpl.get("description", "")[:500],
        assistant_id=assistant_id,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
    )
    db.add(suite)
    db.flush()
    for i, row in enumerate(tpl.get("cases") or []):
        db.add(
            EvalCase(
                suite_id=suite.id,
                input_text=row["input"],
                expected_text=row.get("expected") or "",
                match_type=row.get("match_type") or "contains",
                sort_order=i,
            )
        )
    db.commit()
    db.refresh(suite)
    return ok(suite_dict(suite))


@router.get("/eval/suites")
def list_suites(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(EvalSuite)
        
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
    assistant = ctx.fetch(Assistant, assistant_id)
    if not assistant:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
        return fail(404, "Suite not found")
    db.delete(suite)
    db.commit()
    return ok({"deleted": suite_id})


@router.post("/eval/suites/{suite_id}/cases")
def add_case(suite_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
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
        ctx.query(EvalComparison)
        
        .order_by(EvalComparison.create_time.desc())
        .limit(20)
        .all()
    )
    return ok([comparison_dict(r) for r in rows])


@router.get("/eval/comparisons/trends")
def get_comparison_trends(
    suite_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    return ok(
        {
            "suite_id": suite_id,
            "series": comparison_trends(db, ctx.workspace_id, suite_id=suite_id, limit=limit),
        }
    )


@router.get("/eval/comparisons/{comparison_id}")
def get_comparison(comparison_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    row = ctx.fetch(EvalComparison, comparison_id)
    if not row:
        return fail(404, "Comparison not found")
    return ok(comparison_dict(row))


@router.get("/eval/schedules")
def list_schedules(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(EvalSchedule)
        
        .order_by(EvalSchedule.update_time.desc())
        .all()
    )
    return ok([schedule_dict(r) for r in rows])


@router.post("/eval/schedules")
def create_schedule(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite_id = body.get("suite_id")
    if not suite_id:
        return fail(400, "suite_id required")
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
        return fail(404, "Suite not found")
    interval = max(1, int(body.get("interval_hours") or 24))
    cron_expr = (body.get("cron_expression") or "").strip()
    if cron_expr:
        try:
            cron_expr = validate_cron(cron_expr)
        except ValueError as exc:
            return fail(400, str(exc))
    now = datetime.utcnow()
    sched = EvalSchedule(
        suite_id=suite_id,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        interval_hours=interval,
        cron_expression=cron_expr,
        enabled=1 if body.get("enabled", True) else 0,
        scoring=(body.get("scoring") or "rules").strip().lower(),
        judge_threshold=int(body.get("judge_threshold") or 4),
        webhook_url=(body.get("webhook_url") or "").strip()[:500],
        next_run_at=None,
    )
    sched.next_run_at = compute_schedule_next_run(sched, now)
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
    sched = ctx.fetch(EvalSchedule, schedule_id)
    if not sched:
        return fail(404, "Schedule not found")
    if "enabled" in body:
        sched.enabled = 1 if body["enabled"] else 0
    if "interval_hours" in body:
        sched.interval_hours = max(1, int(body["interval_hours"]))
    if "cron_expression" in body:
        cron_expr = str(body.get("cron_expression") or "").strip()
        if cron_expr:
            try:
                sched.cron_expression = validate_cron(cron_expr)
            except ValueError as exc:
                return fail(400, str(exc))
        else:
            sched.cron_expression = ""
        sched.next_run_at = compute_schedule_next_run(sched)
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
    sched = ctx.fetch(EvalSchedule, schedule_id)
    if not sched:
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
    sched = ctx.fetch(EvalSchedule, schedule_id)
    if not sched:
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
        sched.next_run_at = compute_schedule_next_run(sched, now)
        sched.update_time = now
        db.commit()
        return ok({"run": run_dict(run), "schedule": schedule_dict(sched)})
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/eval/suites/{suite_id}/trends")
def get_suite_trends(
    suite_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
        return fail(404, "Suite not found")
    return ok({"suite_id": suite_id, "points": suite_trends(db, suite_id, ctx.workspace_id, limit=limit)})


@router.get("/eval/alerts")
def list_alerts(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    rows = (
        ctx.query(EvalRegressionAlert)
        
        .order_by(EvalRegressionAlert.update_time.desc())
        .all()
    )
    return ok([alert_dict(r) for r in rows])


@router.post("/eval/alerts")
def create_alert(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite_id = body.get("suite_id")
    if not suite_id:
        return fail(400, "suite_id required")
    suite = ctx.fetch(EvalSuite, suite_id)
    if not suite:
        return fail(404, "Suite not found")
    row = EvalRegressionAlert(
        suite_id=suite_id,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        min_pass_rate=int(body.get("min_pass_rate") or 80),
        drop_points=int(body.get("drop_points") or 10),
        webhook_url=(body.get("webhook_url") or "").strip()[:500],
        pagerduty_routing_key=(body.get("pagerduty_routing_key") or "").strip()[:64],
        opsgenie_api_key=(body.get("opsgenie_api_key") or "").strip()[:128],
        email_to=(body.get("email_to") or "").strip()[:255],
        use_workspace_slack=1 if body.get("use_workspace_slack") else 0,
        cooldown_hours=max(1, int(body.get("cooldown_hours") or 6)),
        enabled=1 if body.get("enabled", True) else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(alert_dict(row))


@router.patch("/eval/alerts/{alert_id}")
def update_alert(
    alert_id: int,
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    row = ctx.fetch(EvalRegressionAlert, alert_id)
    if not row:
        return fail(404, "Alert not found")
    if "min_pass_rate" in body:
        row.min_pass_rate = int(body["min_pass_rate"])
    if "drop_points" in body:
        row.drop_points = int(body["drop_points"])
    if "webhook_url" in body:
        row.webhook_url = str(body["webhook_url"] or "").strip()[:500]
    if "pagerduty_routing_key" in body:
        row.pagerduty_routing_key = str(body["pagerduty_routing_key"] or "").strip()[:64]
    if "opsgenie_api_key" in body and body["opsgenie_api_key"]:
        row.opsgenie_api_key = str(body["opsgenie_api_key"]).strip()[:128]
    if "email_to" in body:
        row.email_to = str(body["email_to"] or "").strip()[:255]
    if "use_workspace_slack" in body:
        row.use_workspace_slack = 1 if body["use_workspace_slack"] else 0
    if "cooldown_hours" in body:
        row.cooldown_hours = max(1, int(body["cooldown_hours"]))
    if "enabled" in body:
        row.enabled = 1 if body["enabled"] else 0
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok(alert_dict(row))


@router.delete("/eval/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    row = ctx.fetch(EvalRegressionAlert, alert_id)
    if not row:
        return fail(404, "Alert not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": alert_id})


@router.get("/eval/runs/{run_id}/diff")
def get_run_diff(
    run_id: int,
    baseline_run_id: int | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    current = ctx.fetch(EvalRun, run_id)
    if not current:
        return fail(404, "Run not found")

    if baseline_run_id:
        baseline = ctx.fetch(EvalRun, baseline_run_id)
        if not baseline:
            return fail(404, "Baseline run not found")
        if baseline.suite_id != current.suite_id:
            return fail(400, "Runs must belong to the same suite")
    else:
        baseline = (
            db.query(EvalRun)
            .filter(EvalRun.suite_id == current.suite_id, EvalRun.id != current.id)
            .order_by(EvalRun.create_time.desc())
            .first()
        )
        if not baseline:
            return fail(400, "No previous run to compare against")

    return ok(diff_eval_runs(current, baseline))


@router.get("/eval/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    run = ctx.fetch(EvalRun, run_id)
    if not run:
        return fail(404, "Run not found")
    return ok(run_dict(run))
