import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import Assistant, EvalCase, EvalRun, EvalSuite, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import fail, ok
from app.services.evaluation import case_dict, run_dict, run_eval_suite, suite_dict

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


@router.post("/eval/suites/{suite_id}/run")
async def run_suite(suite_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    suite = db.get(EvalSuite, suite_id)
    if not suite or suite.workspace_id != ctx.workspace_id:
        return fail(404, "Suite not found")
    if not suite.cases:
        return fail(400, "Add at least one test case before running")
    try:
        run = await run_eval_suite(db, suite, ctx.user.user_id, ctx.workspace_id)
        return ok(run_dict(run))
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/eval/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    run = db.get(EvalRun, run_id)
    if not run or run.workspace_id != ctx.workspace_id:
        return fail(404, "Run not found")
    return ok(run_dict(run))
