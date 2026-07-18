# Workflow Collaboration

## Existing (unchanged)

- **Presence** — `WorkflowPresence`, `WorkflowPresenceSession`
- **Comments** — `WorkflowComment` (marketplace)
- **Versions** — snapshot on edit, restore, diff

Endpoints: `/workflow/{id}/presence`, `/workflow/{id}/versions/*`

## Intelligence additions

- Publish gate requires validation before shared/published workflows
- Audit trail on plan, test, copilot actions via PlatformContext
- Conflict detection via graph validator (structural issues before merge)

## Review mode

Use `POST /workflow/intelligence/publish-check` before publish — returns blockers for team review.

Future: approval workflows hook into `human` nodes + enterprise policies.
