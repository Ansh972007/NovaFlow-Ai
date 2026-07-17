# Developer Security Guide

## Must use

| Concern | Module |
|---------|--------|
| Hash / verify passwords | `app.security.passwords` |
| Issue / rotate / revoke tokens | `app.security.tokens.issue_token_pair` |
| Roles & permissions | `app.security.rbac` |
| Outbound URL fetch | `app.security.ssrf.assert_safe_url` |
| Uploads | `app.security.files.validate_upload` |
| Audit events | `app.security.audit.audit_log` |
| Rate limits | `app.security.rate_limit.rate_limiter` |
| Prompt injection | `app.security.ai_guard` |

## Forbidden patterns

- Storing `md5_hash(password)` for new users
- `httpx.get(user_url)` without `assert_safe_url`
- Accepting JWT via `?t=` on new REST endpoints
- `allow_origins=["*"]` with credentials
- Hardcoding secrets in source

## Adding a new API route

1. Protect with `Depends(get_current_user)` or workspace deps
2. Check `role_has_permission` when action is sensitive
3. Validate bodies with Pydantic models
4. Call `audit_log` for admin/security actions
5. Never trust client-supplied workspace ids without membership check

## Production checklist

- [ ] `NOVAFLOW_ENV=production`
- [ ] Strong `JWT_SECRET` (≥32 random bytes)
- [ ] Strong `NOVAFLOW_ADMIN_PASSWORD` (not admin123)
- [ ] `CORS_ALLOWED_ORIGINS` set to real frontends
- [ ] `PASSWORD_PEPPER` set and backed up
- [ ] TLS terminator + HSTS
- [ ] Database credentials rotated
- [ ] `pip-audit` / dependency scan in CI
- [ ] Review `security_audit_logs` retention
