# Authentication Framework

Location: `backend/app/connectivity/auth.py`

## Supported auth types

OAuth2, OAuth PKCE, API keys, JWT, Bearer, PAT, Basic, SAML, OIDC, AWS IAM, Azure Identity, GCP IAM, webhook, bot_token.

## Validation

`validate_auth_config(auth_type, config)` — checks required fields before connection creation.

## Headers

`auth_headers(auth_type, secret, config)` — builds Authorization headers for outbound calls.

## Scoped credentials

Per-workspace via `connector_credentials` table with version rotation via `connectivity/secrets.py`.
