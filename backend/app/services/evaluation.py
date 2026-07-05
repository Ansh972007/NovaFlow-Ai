import json
import re
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import Assistant, EvalCase, EvalRun, EvalSuite
from app.services.knowledge import rag_context_for_assistant
from app.services.llm import stream_chat_sync


JUDGE_SYSTEM = (
    "You are an expert evaluator for AI assistant responses. "
    "Score how well the actual answer addresses the user question. "
    "If a reference answer is provided, check semantic alignment (not exact wording). "
    'Reply with JSON only: {"score": <1-5>, "pass": <true|false>, "reason": "<brief>"} '
    "Use pass=true when score is 4 or 5."
)


def _score(actual: str, expected: str, match_type: str) -> bool:
    actual = (actual or "").strip()
    expected = (expected or "").strip()
    if match_type == "judge":
        return False  # handled separately
    if not expected:
        return bool(actual)
    if match_type == "exact":
        return actual.lower() == expected.lower()
    return expected.lower() in actual.lower()


async def _llm_judge(
    question: str,
    expected: str,
    actual: str,
    threshold: int = 4,
) -> tuple[bool, str, int]:
    user_block = (
        f"Question:\n{question}\n\n"
        f"Reference answer (optional):\n{expected or '(none)'}\n\n"
        f"Actual answer:\n{actual}\n"
    )
    try:
        raw = await stream_chat_sync(JUDGE_SYSTEM, user_block)
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
            score = int(data.get("score", 0))
            passed = bool(data.get("pass", score >= threshold))
            reason = str(data.get("reason") or "")
            return passed, reason, score
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    # Fallback: substring if reference provided
    if expected:
        passed = expected.lower() in (actual or "").lower()
        return passed, "Fallback substring match", 4 if passed else 2
    passed = bool((actual or "").strip())
    return passed, "Fallback non-empty check", 3 if passed else 1


def suite_dict(suite: EvalSuite, case_count: int | None = None) -> dict:
    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description or "",
        "assistant_id": suite.assistant_id,
        "case_count": case_count if case_count is not None else len(suite.cases or []),
        "create_time": suite.create_time.isoformat() if suite.create_time else None,
        "update_time": suite.update_time.isoformat() if suite.update_time else None,
    }


def case_dict(case: EvalCase) -> dict:
    return {
        "id": case.id,
        "suite_id": case.suite_id,
        "input": case.input_text,
        "expected": case.expected_text or "",
        "match_type": case.match_type or "contains",
        "sort_order": case.sort_order or 0,
    }


def run_dict(run: EvalRun) -> dict:
    try:
        payload = json.loads(run.results_json or "[]")
    except json.JSONDecodeError:
        payload = []
    if isinstance(payload, dict):
        results = payload.get("results", [])
        scoring = payload.get("scoring", "rules")
    else:
        results = payload
        scoring = "rules"
    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "status": run.status,
        "pass_count": run.pass_count,
        "fail_count": run.fail_count,
        "total_count": run.total_count,
        "pass_rate": round((run.pass_count / run.total_count) * 100, 1) if run.total_count else 0,
        "avg_latency_ms": run.avg_latency_ms,
        "scoring": scoring,
        "results": results,
        "create_time": run.create_time.isoformat() if run.create_time else None,
    }


async def run_eval_suite(
    db: Session,
    suite: EvalSuite,
    user_id: int,
    workspace_id: int,
    *,
    scoring: str = "rules",
    judge_threshold: int = 4,
    assistant_id: str | None = None,
    webhook_url: str = "",
) -> EvalRun:
    from app.services.ab_routing import check_eval_quota

    check_eval_quota(db, workspace_id)
    assistant = db.get(Assistant, assistant_id or suite.assistant_id)
    if not assistant:
        raise ValueError("Assistant not found")

    cases = (
        db.query(EvalCase)
        .filter(EvalCase.suite_id == suite.id)
        .order_by(EvalCase.sort_order, EvalCase.id)
        .all()
    )
    results, pass_count, fail_count, latencies = await _run_cases_for_assistant(
        db,
        assistant,
        cases,
        scoring=scoring,
        judge_threshold=judge_threshold,
    )

    total = len(cases)
    avg_ms = int(sum(latencies) / len(latencies)) if latencies else 0
    run = EvalRun(
        suite_id=suite.id,
        user_id=user_id,
        workspace_id=workspace_id,
        status="completed",
        pass_count=pass_count,
        fail_count=fail_count,
        total_count=total,
        avg_latency_ms=avg_ms,
        results_json=json.dumps({"scoring": scoring, "results": results}),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if webhook_url:
        from app.services.webhooks import post_webhook

        await post_webhook(
            webhook_url,
            {
                "suite_id": suite.id,
                "run_id": run.id,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "total_count": total,
                "pass_rate": round((pass_count / total) * 100, 1) if total else 0,
                "avg_latency_ms": avg_ms,
                "scoring": scoring,
            },
            event="eval.completed",
        )

    from app.services.eval_alerts import check_regression_alerts

    await check_regression_alerts(db, suite, run)

    return run


async def _run_cases_for_assistant(
    db: Session,
    assistant: Assistant,
    cases: list[EvalCase],
    *,
    scoring: str = "rules",
    judge_threshold: int = 4,
) -> tuple[list[dict[str, Any]], int, int, list[int]]:
    results: list[dict[str, Any]] = []
    pass_count = 0
    fail_count = 0
    latencies: list[int] = []

    for case in cases:
        start = time.perf_counter()
        user_msg = case.input_text.strip()
        rag = rag_context_for_assistant(db, assistant.id, user_msg)
        system_prompt = assistant.prompt
        if rag:
            system_prompt = (
                f"{assistant.prompt}\n\n"
                "Use the following retrieved context when relevant.\n\n"
                f"--- Context ---\n{rag}\n--- End context ---"
            )
        try:
            output = await stream_chat_sync(system_prompt, user_msg, db=db, workspace_id=assistant.workspace_id)
            error = None
        except Exception as exc:
            output = ""
            error = str(exc)

        latency_ms = int((time.perf_counter() - start) * 1000)
        latencies.append(latency_ms)

        match_type = case.match_type or "contains"
        use_judge = scoring == "judge" or match_type == "judge"
        judge_reason = ""
        judge_score = None

        if use_judge and not error:
            passed, judge_reason, judge_score = await _llm_judge(
                user_msg,
                case.expected_text or "",
                output,
                threshold=judge_threshold,
            )
        else:
            passed = _score(output, case.expected_text or "", match_type) and not error

        if passed:
            pass_count += 1
        else:
            fail_count += 1

        result_item = {
            "case_id": case.id,
            "input": case.input_text,
            "expected": case.expected_text or "",
            "output": output[:4000],
            "passed": passed,
            "latency_ms": latency_ms,
            "error": error,
            "scoring": "judge" if use_judge else match_type,
        }
        if judge_score is not None:
            result_item["judge_score"] = judge_score
            result_item["judge_reason"] = judge_reason
        results.append(result_item)

    return results, pass_count, fail_count, latencies


def schedule_dict(row) -> dict:
    return {
        "id": row.id,
        "suite_id": row.suite_id,
        "interval_hours": row.interval_hours,
        "cron_expression": row.cron_expression or "",
        "enabled": bool(row.enabled),
        "scoring": row.scoring or "rules",
        "judge_threshold": row.judge_threshold or 4,
        "webhook_url": row.webhook_url or "",
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "create_time": row.create_time.isoformat() if row.create_time else None,
    }


def compute_schedule_next_run(sched, base: datetime | None = None) -> datetime:
    from datetime import timedelta

    from app.services.cron_schedule import next_cron_run

    base = base or datetime.utcnow()
    if (sched.cron_expression or "").strip():
        return next_cron_run(sched.cron_expression, base)
    return base + timedelta(hours=max(1, sched.interval_hours or 24))


def comparison_dict(row) -> dict:
    try:
        assistant_ids = json.loads(row.assistant_ids_json or "[]")
    except json.JSONDecodeError:
        assistant_ids = []
    try:
        payload = json.loads(row.results_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": row.id,
        "suite_id": row.suite_id,
        "assistant_ids": assistant_ids,
        "scoring": row.scoring or "rules",
        "assistants": payload.get("assistants", []),
        "create_time": row.create_time.isoformat() if row.create_time else None,
    }


async def run_eval_comparison(
    db: Session,
    suite: EvalSuite,
    assistant_ids: list[str],
    user_id: int,
    workspace_id: int,
    *,
    scoring: str = "rules",
    judge_threshold: int = 4,
) -> "EvalComparison":
    from app.database import EvalComparison
    from app.services.ab_routing import check_eval_quota

    check_eval_quota(db, workspace_id)
    if len(assistant_ids) < 2:
        raise ValueError("Select at least two assistants to compare")

    cases = (
        db.query(EvalCase)
        .filter(EvalCase.suite_id == suite.id)
        .order_by(EvalCase.sort_order, EvalCase.id)
        .all()
    )
    if not cases:
        raise ValueError("Suite has no test cases")

    assistant_results = []
    for aid in assistant_ids:
        assistant = db.get(Assistant, aid)
        if not assistant or assistant.workspace_id != workspace_id:
            raise ValueError(f"Assistant not found: {aid}")
        results, pass_count, fail_count, latencies = await _run_cases_for_assistant(
            db,
            assistant,
            cases,
            scoring=scoring,
            judge_threshold=judge_threshold,
        )
        total = len(cases)
        avg_ms = int(sum(latencies) / len(latencies)) if latencies else 0
        assistant_results.append(
            {
                "assistant_id": assistant.id,
                "assistant_name": assistant.name,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "total_count": total,
                "pass_rate": round((pass_count / total) * 100, 1) if total else 0,
                "avg_latency_ms": avg_ms,
                "results": results,
            }
        )

    comparison = EvalComparison(
        suite_id=suite.id,
        user_id=user_id,
        workspace_id=workspace_id,
        assistant_ids_json=json.dumps(assistant_ids),
        scoring=scoring,
        results_json=json.dumps({"scoring": scoring, "assistants": assistant_results}),
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison
