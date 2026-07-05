import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.database import Assistant, EvalCase, EvalRun, EvalSuite
from app.services.knowledge import rag_context_for_assistant
from app.services.llm import stream_chat_sync


def _score(actual: str, expected: str, match_type: str) -> bool:
    actual = (actual or "").strip()
    expected = (expected or "").strip()
    if not expected:
        return bool(actual)
    if match_type == "exact":
        return actual.lower() == expected.lower()
    return expected.lower() in actual.lower()


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
        results = json.loads(run.results_json or "[]")
    except json.JSONDecodeError:
        results = []
    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "status": run.status,
        "pass_count": run.pass_count,
        "fail_count": run.fail_count,
        "total_count": run.total_count,
        "pass_rate": round((run.pass_count / run.total_count) * 100, 1) if run.total_count else 0,
        "avg_latency_ms": run.avg_latency_ms,
        "results": results,
        "create_time": run.create_time.isoformat() if run.create_time else None,
    }


async def run_eval_suite(db: Session, suite: EvalSuite, user_id: int, workspace_id: int) -> EvalRun:
    assistant = db.get(Assistant, suite.assistant_id)
    if not assistant:
        raise ValueError("Assistant not found")

    cases = (
        db.query(EvalCase)
        .filter(EvalCase.suite_id == suite.id)
        .order_by(EvalCase.sort_order, EvalCase.id)
        .all()
    )
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
            output = await stream_chat_sync(system_prompt, user_msg)
            error = None
        except Exception as exc:
            output = ""
            error = str(exc)

        latency_ms = int((time.perf_counter() - start) * 1000)
        latencies.append(latency_ms)
        passed = _score(output, case.expected_text or "", case.match_type or "contains") and not error
        if passed:
            pass_count += 1
        else:
            fail_count += 1

        results.append(
            {
                "case_id": case.id,
                "input": case.input_text,
                "expected": case.expected_text or "",
                "output": output[:4000],
                "passed": passed,
                "latency_ms": latency_ms,
                "error": error,
            }
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
        results_json=json.dumps(results),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
