# Bharathi purchase invoice OCR

## Provider selection

Environment variables (see `backend/app/core/config.py`):

| Variable | Values | Purpose |
|----------|--------|---------|
| `BHARATHI_OCR_PROVIDER` | `auto`, `mock`, `openai` | Resolver picks implementation |
| `BHARATHI_OCR_MODEL` | e.g. `gpt-4o` | Vision model when using OpenAI |
| `OPENAI_API_KEY` | secret | Required for live OpenAI OCR |

- **`mock`:** Uses real file bytes; returns deterministic structured JSON (tests and local dev without API key).
- **`openai`:** `OpenAIVisionOcrProvider` sends document bytes to the configured vision model.
- **`auto`:** OpenAI when key present; otherwise mock in dev, unconfigured in strict production.

Implementation: `backend/app/services/bharathi/ocr_providers.py`

## Pipeline

1. Supervisor uploads file → `stored_file_id` via existing file storage.
2. Submit → `invoice_workflow` loads bytes (`file_bytes_loader.py`), runs OCR, validates against `invoice_extraction_schema.py`, persists header + `bharathi_purchase_invoice_lines`, runs duplicate detection.

## Live verification status

Automated tests use **`BHARATHI_OCR_PROVIDER=mock`** (`tests/conftest.py`). Live OpenAI OCR is **implemented but not live-verified** without your API key and approval to call external APIs from this environment.