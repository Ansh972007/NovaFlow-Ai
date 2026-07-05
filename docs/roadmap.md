# Roadmap

## v1.8 — Schedules, comparison, webhooks (current)

- [x] Scheduled eval runs — interval-based auto-run with optional webhook on completion
- [x] Multi-assistant comparison — side-by-side pass rates on the same benchmark suite
- [x] Fine-tune job webhooks — notify external URL when training completes or fails

## v1.7 — Eval judge, CSV import, model apply (done)

- [x] LLM-as-judge scoring — subjective pass/fail with score + reason on benchmark runs
- [x] Bulk CSV import — eval cases and fine-tune training rows
- [x] Auto-apply fine-tuned model — set provider `chat_model` from succeeded jobs

## v1.6 — Evaluation & fine-tune (done)

- [x] Benchmark suites — test cases against assistants with RAG, pass/fail scoring
- [x] Eval runs — latency, pass rate, per-case results
- [x] Fine-tune datasets — user/assistant training rows (JSONL export)
- [x] OpenAI fine-tuning jobs — upload, start, status refresh
- [x] Evaluation UI at `/evaluation` (Benchmarks + Fine-tune tabs)

## v1.5 — Multiple model providers + key vault (done)

## v1.4 — Advanced workflow nodes (done)

## v1.3 — Multi-tenant workspaces (done)

## v1.2 — SSO / OAuth (done)

## v1.1 — Admin operations (done)

## v1.0 — Launch (done)

## Future enhancements

| Feature | Notes |
|---------|--------|
| Eval regression alerts | Slack/email when pass rate drops |
| Comparison charts | Visual trend over time |
| Cron expressions | Finer schedule control than hourly intervals |

**NovaFlow v1.8** automates quality checks and makes it easy to compare assistants head-to-head.
