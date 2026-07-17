# Workspace Lifecycle

1. **Create** — personal / team / organization / enterprise via `POST /workspaces` (type, region, timezone, language, default team).
2. **Membership** — owner added automatically; invites by email; roles from workspace ladder.
3. **Switch** — client stores `nf_workspace_id`, sends `X-Workspace-Id`; full reload resets caches/WS.
4. **Operate** — all resources inherit PlatformContext for the active workspace.
5. **Soft-delete** — `Workspace.deleted_at` set; resolve_tenant ignores deleted workspaces.
6. **Quotas** — `WorkspaceQuota` seats / eval / finetune limits.

Invites: pending → accepted | expired | revoked. Accept via `POST /workspaces/invites/accept`.
