# Secret Management

Location: `backend/app/connectivity/secrets.py`

## Features

- Fernet encryption via `app.crypto`
- Credential versioning
- Rotation with `rotate_credential()`
- Masked display via `mask_secret()`

## Storage

`connector_credentials.secret_enc` — never returned in plaintext via API.

## Policy

Scoped to workspace; access requires workspace editor permission.
