# Team Architecture

Teams live **inside** a workspace.

- `Team` — name, slug, optional `parent_team_id` (sub-teams / departments), `leader_user_id`, soft-delete
- `TeamMember` — user ↔ team membership (`lead` | `member`)
- Workspace members may optionally reference `team_id`

Default “General” team is created with new non-personal workspaces.

APIs: `GET/POST /workspaces/{id}/teams`.

Resource visibility `team` (Phase 2 helper in `platform/permissions.py`) restricts to same-team viewers when resources carry `team_id` + `visibility`.
