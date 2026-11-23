"""OCR / vision extraction providers — mock for tests, OpenAI when configured."""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings


class OcrProvider(ABC):
    @abstractmethod
    def extract_invoice(
        self,
        *,
        filename: str,
        mime_type: str,
        file_bytes: bytes,
        hints: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, float]]:
        ...


class MockOcrProvider(OcrProvider):
    def extract_invoice(self, *, filename: str, mime_type: str, file_bytes: bytes, hints: dict[str, Any]):
        _ = file_bytes
        vendor = hints.get("vendor_hint") or "Placeholder Vendor Pvt Ltd"
        invoice_number = f"INV-MOCK-{filename[:12].replace('.', '')}"
        data = {
            "supplier_name": vendor,
            "gstin": "29AAAAA0000A1Z5",
            "supplier_gstin": "29AAAAA0000A1Z5",
            "invoice_number": invoice_number,
            "invoice_date": "2026-04-01",
            "line_items": [
                {
                    "description": "Electrical line material",
                    "quantity": 10,
                    "unit": "pcs",
                    "unit_price": 100.0,
                    "taxable_amount": 1000.0,
                    "line_total": 1000.0,
                }
            ],
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0.0,
            "grand_total": 1180.0,
            "payment_terms": "30 days",
            "currency": "INR",
        }
        confidence = {k: 0.75 for k in ("supplier_name", "supplier_gstin", "invoice_number", "grand_total")}
        return data, confidence


_EXTRACTION_JSON_SCHEMA = """
Return ONLY valid JSON with keys:
supplier_name, supplier_gstin, supplier_address, invoice_number, invoice_date, due_date,
purchase_order_reference, currency, subtotal, discount, freight_other_charges,
cgst, sgst, igst, round_off, grand_total, payment_terms,
line_items (array of objects with description, hsn_sac, quantity, unit, unit_price,
discount_amount, tax_rate, taxable_amount, tax_amount, line_total).
Use null for missing values. Never invent values not visible on the document.
"""


class OpenAIVisionOcrProvider(OcrProvider):
    def extract_invoice(self, *, filename: str, mime_type: str, file_bytes: bytes, hints: dict[str, Any]):
        settings = get_settings()
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise RuntimeError("OCR provider unavailable: OPENAI_API_KEY is not configured")
        from openai import OpenAI

        model = (getattr(settings, "bharathi_ocr_model", None) or settings.openai_model or "gpt-4o-mini").strip()
        client = OpenAI(api_key=api_key, base_url=settings.openai_base_url, timeout=settings.openai_timeout_seconds)
        b64 = base64.standard_b64encode(file_bytes).decode("ascii")
        if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
            content = [
                {"type": "text", "text": _EXTRACTION_JSON_SCHEMA},
                {"type": "file", "file": {"file_data": f"data:application/pdf;base64,{b64}", "filename": filename}},
            ]
        else:
            content = [
                {"type": "text", "text": _EXTRACTION_JSON_SCHEMA},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ]
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        confidence = {k: 0.85 for k in ("supplier_name", "invoice_number", "grand_total")}
        return data, confidence


class UnconfiguredOcrProvider(OcrProvider):
    def extract_invoice(self, *, filename: str, mime_type: str, file_bytes: bytes, hints: dict[str, Any]):
        raise RuntimeError("OCR provider unavailable. Configure OPENAI_API_KEY or use mock in tests only.")


def resolve_provider_name(explicit: str | None = None) -> str:
    settings = get_settings()
    name = (explicit or getattr(settings, "bharathi_ocr_provider", "") or "auto").strip().lower()
    if name == "mock":
        return "mock"
    if name == "openai" or name == "openai_vision" or name == "auto":
        if (settings.openai_api_key or "").strip():
            return "openai_vision"
        return "unconfigured"
    return name


def get_ocr_provider(name: str) -> OcrProvider:
    if name == "mock":
        return MockOcrProvider()
    if name == "openai_vision":
        return OpenAIVisionOcrProvider()
    if name == "unconfigured":
        return UnconfiguredOcrProvider()
    return MockOcrProvider()


def dumps_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)