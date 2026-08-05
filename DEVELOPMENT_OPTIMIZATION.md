# DEVELOPMENT_OPTIMIZATION.md

> Generated for Cursor OOM mitigation on a **16 GB RAM** machine.  
> **No application code, APIs, tests, or database schemas were changed.**  
> Audit date: 2026-08-04

---

## 1. Executive summary

| Metric | Value |
|--------|------:|
| Workspace on-disk size | **~4,480 MB (~4.5 GB)** |
| Dominant folder | `.next/` **~3,448 MB** (Turbopack `.sst` caches) |
| Second | `node_modules/` **~687 MB** |
| Third | `backend/.venv/` **~259 MB** |
| Estimated indexable *before* exclusions | **~60,000+ files** (deps + caches) |
| Estimated indexable *after* `.cursorignore` | **~1,000–1,500 source/config files** (~10–50 MB text) |
| Expected Cursor RAM reduction | **~70–90%** of indexer memory vs indexing `.next` + `node_modules` + `.venv` |

**Root cause of OOM:** Cursor was indexing (or attempting to index) multi‑GB build caches and dependency trees, not the NovaFlow source tree.

---

## 2. Largest folders (on disk)

| Folder | Approx size | Role | Index? |
|--------|------------:|------|--------|
| `.next/` | 3448 MB | Next.js / Turbopack build + dev cache | **Exclude** |
| `node_modules/` | 687 MB | npm dependencies | **Exclude** |
| `backend/` (incl. `.venv`) | ~269 MB | API + local Python venv | Index `app/` only; **exclude `.venv`** |
| `public/` | 36 MB | Static assets (mostly `.glb` models) | Exclude binaries (`*.glb`) |
| `.git/` | 36 MB | Git objects | **Exclude** |
| `data/` | ~1.3 MB | Local runtime data | **Exclude** |
| `src/` | ~1.1 MB | Frontend source | **Index** |
| `docs/` | ~0.1 MB | Documentation | **Index** |

---

## 3. Files larger than 20 MB

| Size (MB) | Path | Recommendation |
|----------:|------|----------------|
| 245.8 | `.next/dev/cache/turbopack/.../00009991.sst` | Exclude + safe to delete with `.next` |
| 245.5 | `.next/dev/cache/turbopack/.../00009056.sst` | Same |
| 245.2 | `.next/dev/cache/turbopack/.../00005142.sst` | Same |
| 244.9 | `.next/dev/cache/turbopack/.../00005692.sst` | Same |
| 242.9 | `.next/dev/cache/turbopack/.../00006227.sst` | Same |
| 242.5 | `.next/dev/cache/turbopack/.../00005143.sst` | Same |
| 218.1 | `.next/dev/cache/turbopack/.../00005846.sst` | Same |
| 206.2 | `.next/dev/cache/turbopack/.../00009992.sst` | Same |
| 177.8 | `.next/dev/cache/turbopack/.../00005850.sst` | Same |
| 143.8 | `.next/dev/cache/turbopack/.../00005845.sst` | Same |
| 139.8 | `.next/dev/cache/turbopack/.../00009987.sst` | Same |
| 130.5 | `node_modules/@next/swc-win32-x64-msvc/...` | Exclude (`node_modules`) |
| 128.8–23.5 | Additional Turbopack `.sst` / webpack packs under `.next/` | Exclude + deletable |
| 124.3 | `node_modules/next/.../swc-linux-x64-gnu/...` | Exclude |
| 124.2 | `node_modules/next/.../swc-linux-x64-musl/...` | Exclude |
| 22.4 | `public/models/nova.glb` | **Keep in repo**; **exclude from Cursor index** (`*.glb`) |

All files >20 MB except `public/models/nova.glb` are **generated or dependency binaries** and must not be indexed.

---

## 4. Estimated indexed files

| Scope | Approx file count |
|-------|------------------:|
| `.next/` | ~4,400 |
| `node_modules/` | ~27,600 |
| `backend/.venv/` | ~13,300 |
| `src/` | ~150 |
| `backend/app/` | ~800 |
| `docs/` | ~100 |
| **Whole tree (naive)** | **~62,000** |
| **After `.cursorignore` (source focus)** | **~1,000–1,500** |

---

## 5. Recommended exclusions (implemented in `.cursorignore`)

Already covered:

- `node_modules`, `.next`, `dist`, `build`, `out`, `coverage`
- `.pytest_cache`, `__pycache__`, `.venv` / `venv`
- `logs`, `tmp`, `cache`, `uploads`, `storage`, `artifacts`, `media`, `screenshots`
- Docker / DB volume dirs, vector DB dumps
- Binary assets: `*.glb`, `*.wasm`, archives, model weights
- `.git`, secrets (`.env*`), IDE folders

---

## 6. `.gitignore` audit

**Already present:** `node_modules`, `.next`, `out`, `build`, `coverage`, `__pycache__`, `backend/data/`, `.env*`.

**Added / reinforced:** `.venv` / `venv`, pytest/mypy/ruff caches, `.turbo`, logs/tmp, uploads/storage/artifacts, local docker volume folder names, IDE junk.

**Not tracked by git (good):** `.next/`, `node_modules/`, `backend/.venv/` — confirmed zero tracked paths under these.

**Tracked large asset (intentional):** `public/models/nova.glb` (~22 MB) — production frontend asset; keep in git; excluded from Cursor via `*.glb`.

---

## 7. Duplicated / redundant generated assets (cleanup report — **no deletes performed**)

| Item | Notes | Safe action |
|------|-------|-------------|
| Turbopack `.sst` shards under `.next/dev/cache/turbopack/` | Many 100–250 MB files; regenerable | Delete entire `.next/` when Cursor is closed |
| Nested `node_modules` under packages | Normal npm layout, not true duplicates | Leave; already ignored |
| Multiple `__pycache__` trees | Normal Python bytecode | Leave; already ignored; optional `find` clean |
| `backend/.venv` | Local env duplicate of Docker image deps | Leave for local API; **never open as workspace root** |
| Linux SWC binaries inside Windows `node_modules` | Platform fallbacks from Next | Leave; ignored |

**Do not auto-delete** production assets under `public/models/`.

---

## 8. Folders that should not be in the active Cursor workspace

Treat as **out of band** (ignored or open in a separate lighter window only if needed):

1. `.next/`
2. `node_modules/`
3. `backend/.venv/`
4. `data/` and any docker volume mounts
5. `.git/`
6. Binary-heavy `public/models/` (via ignore patterns; folder can stay)

---

## 9. Recommended workspace structure for development

Prefer a **multi-root** or **focused** workspace instead of indexing the entire monorepo dump:

```text
NovaFlow/                    # optional: open ONLY these roots in Cursor
  backend/app/               # API source
  backend/tests/             # tests (optional second root)
  src/                       # Next.js app source
  docs/                      # product docs
  deploy/                    # compose / ops (optional)
  scripts/                   # helper scripts (optional)
```

**Practical options (16 GB RAM):**

1. **Best:** Keep opening repo root, but rely on `.cursorignore` (done).
2. **Stronger:** Create `novaflow-dev.code-workspace` with folders `src`, `backend/app`, `docs` only.
3. **When editing Docker only:** open `deploy/` as a separate tiny window.

Example `novaflow-dev.code-workspace` (create manually if desired):

```json
{
  "folders": [
    { "path": "src", "name": "frontend" },
    { "path": "backend/app", "name": "backend" },
    { "path": "docs", "name": "docs" },
    { "path": ".", "name": "repo-root-configs" }
  ],
  "settings": {
    "files.watcherExclude": {
      "**/.next/**": true,
      "**/node_modules/**": true,
      "**/.venv/**": true,
      "**/__pycache__/**": true
    },
    "search.exclude": {
      "**/.next": true,
      "**/node_modules": true,
      "**/.venv": true
    }
  }
}
```

Note: If you include `"."` as a folder, `.cursorignore` is still critical.

---

## 10. Cursor configuration (`.cursor`)

| Check | Result |
|-------|--------|
| `.cursor/` project folder | **Not present** — no heavy rules/indexing config found |
| Action | No regeneration required; avoid adding large rule corpora or embedding indexes into `.cursor` |

Minimal future policy: keep `.cursor/rules` small; never put build outputs or datasets under `.cursor/`.

---

## 11. Memory optimization suggestions (16 GB machine)

1. **Restart Cursor after adding `.cursorignore`** so the index rebuilds from exclusions.
2. **Safe disk reclaim:** with Docker/dev servers stopped, delete `.next/` (`Remove-Item -Recurse -Force .next`) — frees ~3.4 GB; rebuilds on next `npm run dev` / Docker build.
3. Prefer **Docker** for API/web when possible so host does not need both heavy `.next` *and* full local builds.
4. Close other Chromium/Electron apps while indexing.
5. Disable unnecessary Cursor features that re-scan the tree (extra MCP file watchers, huge chat attachments of whole repos).
6. Do **not** open `node_modules` or `.venv` as workspace folders.
7. For local Next builds on 16 GB, prefer webpack (`next build --webpack`) over Turbopack if Turbopack cache balloons again.

---

## 12. Safe cleanup suggestions (manual)

```powershell
# From repo root — SAFE generated cleanup (does NOT touch source)
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache, coverage, .turbo -ErrorAction SilentlyContinue
```

**Optional (larger reclaim, still safe for “reinstallable” deps):**

```powershell
# Only if you can re-run npm install / recreate venv
# Remove-Item -Recurse -Force node_modules
# Remove-Item -Recurse -Force backend\.venv
```

**Do not delete:** `src/`, `backend/app/`, `public/models/`, `docs/`, compose files, `.env.example`.

---

## 13. Expected RAM reduction

| Scenario | Rough indexer working set |
|----------|---------------------------|
| Indexing everything (~4.5 GB tree) | High — often **OOM on 16 GB** with Electron + Docker |
| After `.cursorignore` only | **Much lower** — source ~1–5 MB + docs; binaries skipped |
| After `.cursorignore` + delete `.next` | Lowest disk pressure; indexer stays on source |
| Multi-root (`src` + `backend/app` only) | Lowest Cursor footprint |

**Conservative estimate:** excluding `.next` + `node_modules` + `.venv` removes **~4.4 GB** from the scan surface and typically **several GB of peak RAM** during initial indexing.

---

## 14. Changes made in this optimization pass

| File | Action |
|------|--------|
| `.cursorignore` | **Created** — production-grade exclusions |
| `.gitignore` | **Updated** — reinforce venv/cache/runtime ignores |
| `DEVELOPMENT_OPTIMIZATION.md` | **Created** — this report |
| Application code / APIs / tests / DB | **Unchanged** |

---

## 15. Next steps for you

1. Close and reopen the NovaFlow folder in Cursor (or Reload Window).
2. Confirm indexing finishes without `reason: 'oom'`.
3. Optionally run the safe `.next` cleanup above to reclaim ~3.4 GB disk.
4. If OOM persists, open `novaflow-dev.code-workspace` with only `src` + `backend/app` + `docs`.

---

## 16. Cursor + Docker coexistence (16 GB RAM) — REQUIRED MODE

On 16 GB machines, **full Docker + Cursor** competes for RAM and causes OOM / Docker Desktop crashes.
Use the **Cursor-safe stack** below. I (the agent) verify health; you should not need to babysit builds.

### What changed

| Change | Purpose |
|--------|---------|
| `%USERPROFILE%\.wslconfig` memory=4GB | Caps Docker/WSL so Cursor keeps ~10+ GB |
| `docker-compose.cursor.yml` | Memory limits; **no Milvus**; no image rebuild |
| `scripts/cursor-stack-up.ps1` | One-command start + health verify |
| `scripts/cursor-stack-down.ps1` | Clean stop |
| `scripts/apply-docker-ram-cap.ps1` | Apply WSL cap + restart Docker once |

### Daily workflow (you)

```powershell
# First time only (after clone / RAM-cap change):
.\scripts\apply-docker-ram-cap.ps1

# Every day — keep Cursor open:
.\scripts\cursor-stack-up.ps1

# When done coding for the day:
.\scripts\cursor-stack-down.ps1
```

### Agent / build policy (no user verification needed)

1. Prefer **Cursor-safe stack** (`cursor-stack-up.ps1`) — never `docker compose up --build` while Cursor is open.
2. Rebuild **web** image only when Cursor is closed (or on a machine with more RAM).
3. API-only rebuilds are lighter and OK if needed: `docker compose build api`.
4. Full Milvus stack: `docker compose --profile full up -d` (not for daily Cursor use).

### Memory budget (target)

| Component | Target |
|-----------|-------:|
| Docker/WSL VM | <= 4 GB |
| Containers combined | ~1.2–2.0 GB |
| Cursor + Windows | remainder (~10+ GB) |

### URLs

- Web: http://localhost:3000
- API: http://localhost:3001/health
- Login: set `NOVAFLOW_ADMIN_PASSWORD` (≥16 chars) before first boot