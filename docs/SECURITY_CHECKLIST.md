# Security Checklist — production gate

## Before go-live

- [ ] `NOVAFLOW_ENV=production`
- [ ] Unique `JWT_SECRET` (≥32 cryptographically random bytes)
- [ ] `NOVAFLOW_ADMIN_PASSWORD` strong (boot fails on admin123 in prod)
- [ ] `PASSWORD_PEPPER` set and stored in secret manager
- [ ] `CORS_ALLOWED_ORIGINS` = exact frontend origins only
- [ ] TLS terminated; HSTS active
- [ ] Database not exposed publicly
- [ ] Redis not exposed publicly
- [ ] Milvus not exposed publicly
- [ ] File upload volume permissions reviewed
- [ ] `pip-audit` / dependency scan clean or risk-accepted
- [ ] Security CI workflow green
- [ ] Backup + restore tested
- [ ] Incident response owner assigned
- [ ] Audit log retention policy defined

## Post-deploy verification

- [ ] Login issues access + refresh tokens
- [ ] Expired access token refreshes silently
- [ ] Logout invalidates refresh (reuse fails)
- [ ] `web_fetch` to 169.254.169.254 blocked
- [ ] Login rate limit returns 429 after burst
- [ ] `/health` reports `"security": "enterprise-v1"`
- [ ] Non-root container user confirmed (`novaflow`)
