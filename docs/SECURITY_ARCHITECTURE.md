# NovaFlow Enterprise Security Architecture
# Version: 9.9.0 / security-foundation-v1
#
# This document defines the permanent security model. Future features MUST
# inherit these controls via app.security.* — do not re-implement auth,
# hashing, SSRF, or rate limiting in routers.

## Trust Boundaries

1. Browser / untrusted client
2. Next.js BFF proxy (`/api/v1/*`)
3. FastAPI application (authenticated zone)
4. Data plane: MySQL/SQLite, Redis, Milvus, object uploads
5. External egress: LLM providers, integrations, webhooks, agent web_fetch

## Authentication Flow

1. Client fetches RSA-2048 public key (`GET /user/public_key`)
2. Password encrypted client-side (JSEncrypt) for transport
3. Server decrypts → Argon2id verify (legacy MD5 auto-upgraded on success)
4. Server issues:
   - Access token (JWT, ~15 min, HS256, issuer-bound, session id)
   - Refresh token (opaque, hashed at rest, family rotation)
5. Session row in `auth_sessions` with device fingerprint + absolute expiry
6. Refresh via `POST /user/refresh` rotates token; reuse of revoked token
   invalidates the entire family (theft detection)
7. Logout revokes refresh + session (`POST /user/logout`)

## Authorization

Roles (rank ascending): guest < viewer < analyst < editor < developer <
manager < admin < workspace_owner < super_admin

Legacy `admin|editor|viewer` remain valid. Platform user_id=1 maps to
`super_admin`. Fine-grained `Permission` enum in `app.security.rbac`.

Workspace isolation via `X-Workspace-Id` + membership check in `deps.py`.

## Password Policy

- Argon2id (time/memory/parallelism configurable)
- Optional PASSWORD_PEPPER
- History of last 5 hashes (reuse blocked on change)
- Transparent MD5 → Argon2id migration on login
- Production refuses default JWT_SECRET and admin123

## API Hardening

- Security headers middleware (CSP, XFO, nosniff, Referrer-Policy, HSTS)
- Strict CORS allowlist (`CORS_ALLOWED_ORIGINS`)
- Rate limits: login / API / upload / websocket
- Max request body size
- REST auth: Bearer header only (no `?t=` query tokens on REST)
- Audit log table + structured logger (`security_audit_logs`)

## File Uploads

`app.security.files.validate_upload`:
extension allowlist, magic-byte checks, executable rejection,
filename sanitization, size cap (`MAX_UPLOAD_BYTES`).

## SSRF

`assert_safe_url` used by agent `web_fetch`, webhooks, knowledge URL ingest.
Blocks localhost, link-local, private IPs (unless SSRF_ALLOW_PRIVATE=1),
cloud metadata, and follows no redirects.

## AI Guards

`detect_prompt_injection` / `sanitize_user_prompt` for instruction-override
patterns. Integrate on chat/workflow entry points for new features.

## Database

- Security tables: auth_sessions, refresh_tokens, password_history,
  security_audit_logs
- Alembic under `backend/alembic` for forward migrations
- Boot still runs create_all + migrate_schema for compatibility

## Docker

- API container runs as non-root `novaflow` user
- Healthcheck on `/health`
- Set `NOVAFLOW_ENV=production`, strong `JWT_SECRET`,
  `NOVAFLOW_ADMIN_PASSWORD`, `CORS_ALLOWED_ORIGINS`, optional `PASSWORD_PEPPER`

## Incident Response (summary)

1. Revoke sessions: `POST /user/logout_all` or DB revoke on auth_sessions
2. Rotate JWT_SECRET (invalidates all access tokens; force re-login)
3. Rotate PASSWORD_PEPPER only with coordinated password resets
4. Inspect `security_audit_logs` for auth.login.failed / reuse_detected
5. Block egress / disable web_fetch via feature flags if needed

## Developer Rules

- Never call `md5_hash` for new password storage
- Never fetch arbitrary URLs without `assert_safe_url`
- Never accept access tokens from query strings on new REST routes
- Use `issue_token_pair` for all interactive logins
- Use `audit_log` for security-sensitive actions
- Add Alembic revisions for schema changes in production paths
