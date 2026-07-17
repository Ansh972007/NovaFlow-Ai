# Permission Matrix (Workspace)

Workspace roles (customer tenant):

`guest` < `viewer` < `analyst` < `editor` < `developer` < `manager` < `admin` < `owner`

Platform roles (`super_admin`, support) do **not** grant workspace data access without Emergency Access.

| Permission | Min role |
|------------|----------|
| workspace:read | guest |
| workspace:write | editor |
| workspace:admin | admin |
| workspace:billing | owner |
| assistant:read | viewer |
| assistant:write | editor |
| assistant:publish | editor |
| knowledge:read | viewer |
| knowledge:write | editor |
| knowledge:delete | admin |
| workflow:read | viewer |
| workflow:write | editor |
| workflow:run | editor |
| workflow:publish | editor |
| agent:read | viewer |
| agent:run / write | editor |
| eval:read / run | analyst |
| eval:write | developer |
| modellab:read / write | developer |
| integration:read / write | admin |
| analytics:read | analyst |
| analytics:export | admin |
| apikey:manage | developer |
| marketplace:publish | editor |
| team:manage | admin |
| security:audit | admin |

Emergency access grants **read** permissions only (`*_READ`, analytics read, security audit).

Runtime check: `ctx.require(Permission.X)` / `require_permission(Permission.X)`.
