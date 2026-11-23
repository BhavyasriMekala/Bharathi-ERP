"""OCR / vision extraction providers (mock default; OpenAI optional via env)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class OcrProvider(ABC):
    @abstractmethod
    def extract_invoice(self, *, filename: str, mime_type: str, hints: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float]]:
        ...


class MockOcrProvider(OcrProvider):
    def extract_invoice(self, *, filename: str, mime_type: str, hints: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float]]:
        vendor = hints.get("vendor_hint") or "Placeholder Vendor Pvt Ltd"
        invoice_number = f"INV-MOCK-{filename[:12].replace('.', '')}"
        data = {
            "vendor_name": vendor,
            "gstin": "29AAAAA0000A1Z5",
            "invoice_number": invoice_number,
            "invoice_date": "2026-04-01",
            "line_items": [
                {
                    "description": "Electrical line material",
                    "quantity": 10,
                    "unit_price": 100.0,
                    "taxable_amount": 1000.0,
                }
            ],
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0.0,
            "total_gst": 180.0,
            "invoice_total": 1180.0,
            "payment_terms": "30 days",
            "purchase_order_reference": None,
        }
        confidence = {k: 0.75 for k in ("vendor_name", "gstin", "invoice_number", "invoice_total")}
        return data, confidence


class OpenAIVisionOcrProvider(OcrProvider):
    """BLOCKED EXTERNAL without OPENAI_API_KEY — not invoked in tests."""

    def extract_invoice(self, *, filename: str, mime_type: str, hints: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float]]:
        raise NotImplementedError("Configure OPENAI_API_KEY and image pipeline before enabling vision OCR.")


def get_ocr_provider(name: str) -> OcrProvider:
    if name == "openai_vision":
        return OpenAIVisionOcrProvider()
    return MockOcrProvider()


def dumps_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)