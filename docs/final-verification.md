# Final verification checklist (v9.9)

Run from `novaflow-ai/`:

```bash
npm run verify          # lint + backend smoke tests
npm run build           # production frontend build
```

Or backend only:

```bash
cd backend
python -m pytest -q
```

## Covered by automated smoke (`backend/tests/test_smoke.py`)

- Health `/health` version 9.9.0
- Login + `/user/info`
- Unauthorized access blocked
- Workflow templates, create, run, runs list/detail
- Knowledge create/list
- Agents tools + run + save
- Integrations health/settings
- Schedules list
- Model Lab pipelines/drift + eval suites
- Batch workflow run
- Unit: titled-field parse, notify limits, calc sandbox, prompts

## Manual UI pass (after `npm run dev` + backend)

1. Login `admin` / `admin123`
2. Chat → send a message
3. Knowledge → create KB (upload optional)
4. Workflows → create from Support template → Run
5. Runs → see status badge
6. Agents → run with word_count
7. Digests → schedules list
8. Settings → Integrations health
9. Developer → Health + List runs presets
10. Evaluation / Model Lab load without error

## Known non-blockers

- External integrations (Slack/Gmail/Jira/…) need credentials in Settings
- LLM quality depends on provider keys in Settings
- Default JWT/admin secrets are for local/dev only
