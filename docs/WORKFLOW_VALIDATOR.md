# Workflow Validator

Location: `backend/app/workflow_intelligence/graph/validator.py`

## Checks

| Code | Severity | Description |
|------|----------|-------------|
| `empty_graph` | error | No nodes |
| `duplicate_node_id` | error | Duplicate ids |
| `dangling_edge` | error | Edge references missing node |
| `self_loop` | error | Node connects to itself |
| `cycle_detected` | error | Circular execution |
| `unreachable_node` | warning | Not reachable from trigger |
| `disconnected_node` | warning | No edges |
| `missing_trigger` | warning | No trigger node |
| `missing_knowledge` | warning | Retrieve without KB |
| `missing_url` | error | HTTP node without URL |
| `invalid_expression` | error | Unclosed `{{` template |

## API

`POST /api/v1/workflow/intelligence/validate`

Returns validation + security reports.

## Publish integration

`check_publish_ready()` blocks publish on errors (see `WORKFLOW_EXECUTION.md`).

## Score

0–100 based on errors (−15) and warnings (−5).
