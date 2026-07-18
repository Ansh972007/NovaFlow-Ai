# Workflow Testing

Location: `backend/app/workflow_intelligence/testing/runner.py`

## Test types

| Type | Support |
|------|---------|
| Integration | Full `run_workflow()` |
| Mock/dry-run | `mock_mode=true` — validate only |
| Regression | Saved `WorkflowTestCase` rows |
| Copilot-generated | `copilot/tests` endpoint |

## Storage

`workflow_test_cases` table — tenant-scoped via `workspace_id`.

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /workflow/intelligence/tests` | Create test case |
| `GET /workflow/intelligence/tests?workflow_id=` | List |
| `POST /workflow/intelligence/tests/run` | Run all saved tests |
| `POST /workflow/intelligence/tests/run-one` | Ad-hoc run |
| `POST /workflow/intelligence/copilot/tests` | Generate test ideas |

## Assertions

`expected_contains` — substring match on output.

## Audit

`workflow.test.create`, `workflow.test.run`
