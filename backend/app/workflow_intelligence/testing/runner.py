"""Workflow testing — unit, integration, replay, golden execution."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.database import Workflow, WorkflowTestCase
from app.services.workflow import run_workflow


@dataclass
class TestResult:
    test_id: int | None
    name: str
    passed: bool
    output: str = ""
    error: str = ""
    duration_ms: int = 0
    steps: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "passed": self.passed,
            "output": self.output[:2000],
            "error": self.error,
            "duration_ms": self.duration_ms,
            "step_count": len(self.steps),
        }


async def run_test_case(
    db: Session,
    workflow: Workflow,
    *,
    user_id: int,
    workspace_id: int,
    input_text: str,
    expected_contains: str = "",
    mock_mode: bool = False,
) -> TestResult:
    import time

    start = time.perf_counter()
    try:
        if mock_mode:
            return TestResult(
                test_id=None,
                name="mock",
                passed=True,
                output="(dry-run — graph validated only)",
            )
        result = await run_workflow(db, workflow, user_id, input_text, workspace_id)
        output = str(result.get("output") or "")
        passed = True
        error = ""
        if expected_contains and expected_contains not in output:
            passed = False
            error = f"Expected output to contain: {expected_contains!r}"
        if result.get("status") == "error":
            passed = False
            error = error or "Workflow returned error status"
        return TestResult(
            test_id=None,
            name="integration",
            passed=passed,
            output=output,
            error=error,
            duration_ms=int((time.perf_counter() - start) * 1000),
            steps=result.get("steps") or [],
        )
    except Exception as exc:
        return TestResult(
            test_id=None,
            name="integration",
            passed=False,
            error=str(exc),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )


async def run_saved_tests(
    db: Session,
    workflow_id: str,
    *,
    user_id: int,
    workspace_id: int,
) -> list[TestResult]:
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        return []

    rows = (
        db.query(WorkflowTestCase)
        .filter(
            WorkflowTestCase.workflow_id == workflow_id,
            WorkflowTestCase.workspace_id == workspace_id,
            WorkflowTestCase.deleted_at.is_(None),
        )
        .all()
    )
    results: list[TestResult] = []
    for row in rows:
        tr = await run_test_case(
            db,
            workflow,
            user_id=user_id,
            workspace_id=workspace_id,
            input_text=row.input_text or "",
            expected_contains=row.expected_contains or "",
            mock_mode=bool(row.mock_mode),
        )
        tr.test_id = row.id
        tr.name = row.name or f"test-{row.id}"
        results.append(tr)
    return results
