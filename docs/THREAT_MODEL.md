# NovaFlow Threat Model (STRIDE summary)
# Companion to docs/SECURITY_ARCHITECTURE.md

## Assets

- User credentials & sessions
- Workspace secrets (LLM keys, Slack/Jira/GitHub tokens)
- Knowledge documents & embeddings
- Workflow graphs & execution logs
- Audit trails

## Actors

- Anonymous internet user
- Authenticated member (viewer→admin)
- Compromised account / stolen refresh token
- Malicious workspace member (insider)
- External webhook caller

## Key Threats & Controls

| Threat | Control |
|--------|---------|
| Credential stuffing | Rate limit login; Argon2id; audit failures |
| Password DB leak | Argon2id + optional pepper; no MD5 for new hashes |
| Token theft (XSS) | Short access TTL; refresh rotation; family revoke on reuse |
| Session fixation | New session id per login |
| SSRF via tools/webhooks | assert_safe_url; no redirects; block metadata IPs |
| Privilege escalation | RBAC ranks; workspace membership checks |
| Upload malware | Magic bytes; extension allowlist; size limits |
| Prompt injection | ai_guard detectors (extend on chat paths) |
| CORS abuse | Explicit origin allowlist |
| Insecure defaults | Production boot fails on weak JWT/admin password |
| Log leakage of tokens | REST rejects query-string tokens |

## Residual Risks (accepted / future)

- Full TOTP MFA enrollment UI (schema ready: mfa_enabled/mfa_secret_enc)
- Virus scanning (interface via validate_upload extension point)
- Vault/HSM-backed JWT_SECRET rotation automation
- Redis-backed distributed rate limits (in-process today; swap RateLimiter backend)
