# Real-data verification (formats · models · training)

## Automated (no API key required)

```bash
cd novaflow-ai
npm run test:backend
# or focused:
npm run test:pipeline
```

Covers **one-by-one**:

| Format | Parser | Upload → Ready → Search |
|--------|--------|-------------------------|
| `.txt` / `.md` | text | yes |
| `.csv` / `.tsv` | structured rows | yes |
| `.json` | flattened keys | yes |
| `.html` | stripped | yes |
| `.pdf` | pypdf | yes |
| `.docx` | OOXML | yes |
| `.xlsx` | OOXML | yes |
| `.pptx` | OOXML | yes |
| `.doc` / `.xls` / `.ppt` | rejected with clear error | blocked |

Also verifies:

- Knowledge → dataset JSONL build (train path)
- Training CSV import (`user` / `assistant` / `system`)
- RAG retrieval + demo-mode chat that **surfaces retrieved evidence**
- Live OpenAI train/chat **skipped** until `LIVE_OPENAI_API_KEY` is set

## Live LLM + fine-tune (paid)

```powershell
$env:LIVE_OPENAI_API_KEY = "sk-..."
cd novaflow-ai\backend
python -m pytest tests/test_real_pipeline.py::test_live_provider_chat_and_optional_train -q
```

Or in the UI:

1. **Settings → Model providers → + Add provider** (OpenAI + API key) → activate  
2. **Knowledge** → upload PDF/CSV/DOCX/… → wait for **Ready** → Q&A preview  
3. **Apps** → link KB to assistant → **Chat** (answers should cite docs)  
4. **Model Lab** → select Ready KBs → Generate dataset → Train (`gpt-4o-mini-2024-07-18`) → Refresh → Deploy  

Embeddings and OCR now use the **Settings vault key** (not only `OPENAI_API_KEY` env).

## Blind spots closed in this pass

- Embeddings ignored Settings vault (env-only) → **fixed**
- CSV ingested as raw blob → **structured rows**
- XLSX / PPTX UI claim without parsers → **real OOXML parsers**
- Legacy `.doc` accept → **rejected with message + Retry UX**
- `/knowledge/retry` stub → **reprocesses file**
- Q&A preview keyword-only → **`/knowledge/search` semantic**
- Demo chat hid RAG → **shows retrieved evidence**
- OCR ignored vault/base URL → **uses active provider**
