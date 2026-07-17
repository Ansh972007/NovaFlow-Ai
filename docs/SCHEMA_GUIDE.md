# Schema Guide

## Logical domains

| Domain | Tables (representative) |
|--------|-------------------------|
| Identity | `users`, `auth_sessions`, `refresh_tokens`, `password_history` |
| Platform | `organizations`, `organization_members` |
| Workspace | `workspaces`, `workspace_members`, `workspace_invites`, `workspace_quotas`, `teams`, `team_members` |
| Knowledge | `knowledge_bases`, `knowledge_files`, `knowledge_chunks`, `assistant_knowledge` |
| Workflow | `workflows`, `workflow_versions`, `workflow_schedules`, `workflow_presence*` |
| Agent | `saved_agents`, `assistants` |
| Execution | `workflow_runs`, `workflow_pending_runs` (+ `workflow_runs_p` on PG) |
| Analytics | `usage_events` |
| Marketplace | `workflow_ratings`, `workflow_comments` |
| Evaluation | `eval_suites`, `eval_cases`, `eval_runs`, `eval_schedules`, … |
| Storage | `object_files` |
| Security / Audit | `security_audit_logs`, `emergency_access_grants`, `api_keys` (+ `security_audit_logs_p`) |
| System | `llm_providers`, `workspace_settings`, `ab_model_routes`, integrations |

## Normalization

- Correctness-critical relations are normalized (memberships, invites, grants).
- Large JSON blobs (`graph_json`, `results_json`) are intentional denormalizations for document-style workflow/eval payloads — documented tradeoff: fewer joins at write time; archive/partition for growth.

## Soft delete

Default path: set `deleted_at`. Restore clears it. Purge requires retention elapsed + `confirm=true` and no `legal_hold`.

## Object files

`object_files` stores provider, key, checksum, size, tenant columns. Bytes never enter the RDBMS.
