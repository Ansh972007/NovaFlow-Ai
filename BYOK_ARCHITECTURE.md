# BYOK (Bring Your Own Key) Security Architecture

NovaFlow enforces industry-standard security paradigms for storing and utilizing user-provided API credentials.

---

## 1. Encrypted Storage Flow
All API keys entered into the **AI Providers** settings hub undergo local symmetric encryption before database insertion:
1. **Key Generation**: A unique environment-level master key (`ENCRYPT_KEY`) is loaded during API startup.
2. **Encryption**: Keys are encrypted via AES-GCM (256-bit key length) to generate a secure hex payload.
3. **Storage**: The encrypted string is written to the `api_key_enc` column of the `llm_providers` table.

---

## 2. In-Memory Decryption
API keys are never returned in plaintext to the frontend client:
- The `/api/v1/settings/providers` list endpoint masks API keys, returning only the last 4 characters as a hint (e.g., `••••sk-4b3c`).
- Decryption happens exclusively in-memory inside the sandboxed backend process during inference completions.

---

## 3. Workspace Isolation
Each API key is mapped to a tenant or workspace identifier, preventing cross-tenant leakage or unauthorized key reuse.
