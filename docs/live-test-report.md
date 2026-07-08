# NovaFlow live test report (senior QA)

- Passed: **26**
- Failed: **0**
- OpenAI quota blocked: **False**

## Verdict

All live checks including chat expected answers passed.

## Passed

- PASS `api_key_present` — provider=OpenRouter Live model=openai/gpt-4o-mini
- PASS `openai_key_authenticates` — 343 models listed
- PASS `openai_quota` — chat completions usable
- PASS `login` — admin
- PASS `settings_provider_saved` — vault activated
- PASS `create_knowledge` — id=3
- PASS `process_handbook.txt` — Ready
- PASS `process_policy.md` — Ready
- PASS `process_catalog.csv` — Ready
- PASS `process_meta.json` — Ready
- PASS `process_page.html` — Ready
- PASS `process_clause.docx` — Ready
- PASS `process_deck.pptx` — Ready
- PASS `process_sheet.xlsx` — Ready
- PASS `process_guide.pdf` — Ready
- PASS `formats_ready_count` — 9/9
- PASS `knowledge_search` — method=vector hits=5
- PASS `url_fetch_ingest` — https://example.com
- PASS `reject_legacy_doc` — blocked
- PASS `assistant_rag_linked` — e943ed4a
- PASS `rag_context_built` — chars=488
- PASS `chat_expected_answer` — NovaFlowUniqueMarkerX9Z
- PASS `chat_refund_days` — Refunds take 14 days.
- PASS `model_lab_dataset_from_docs` — rows=9
- PASS `finetune_skipped_openrouter` — use native OpenAI key for train jobs
- PASS `workflow_llm_run` — ## Classification Priority: P2 · Category: Account Security · Sentiment: Neutral  ## Customer reply I’m really sorry to hear that you’re hav

## Failed

- None

## Notes

- OpenRouter does not host OpenAI fine-tuning jobs — dataset JSONL path verified only

## Chat samples

**Q:** What is the warranty code? Reply with the exact code from the docs.

**A:** NovaFlowUniqueMarkerX9Z

**Q:** How many days do refunds take?

**A:** Refunds take 14 days.


## Security

Key stored only in gitignored `backend/.env`. **Rotate this OpenRouter key** — it was pasted into chat and should be treated as exposed.
