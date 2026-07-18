# Export Engine

Location: `backend/app/conversation/export.py`

## Formats

| Format | Support |
|--------|---------|
| Markdown | ✅ Default |
| JSON | ✅ Full structured export |
| HTML | ✅ Basic rendering |
| PDF | 🔜 (via external renderer) |
| DOCX | 🔜 |

## API

`GET /api/v1/conversations/{id}/export?fmt=markdown|json|html`

## Import

Use JSON export format for round-trip import (future endpoint).
