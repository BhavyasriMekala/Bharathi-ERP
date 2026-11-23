"""Read-only TallyPrime connector abstraction (fixture-tested; live Tally not verified)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class TallyReadOnlyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TallyCompanyIdentity:
    name: str
    guid: str | None = None


@dataclass(frozen=True, slots=True)
class TallySupplierLedger:
    name: str
    closing_balance: Decimal
    guid: str | None = None
    gstin: str | None = None


@dataclass(frozen=True, slots=True)
class TallyPurchaseVoucher:
    voucher_number: str
    voucher_type: str
    party_name: str
    amount: Decimal
    voucher_date: str | None
    tally_guid: str | None = None


class TallyReadOnlyConnector(ABC):
    """Read-only interface — no write methods."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def company_identity(self) -> TallyCompanyIdentity:
        ...

    @abstractmethod
    def list_supplier_ledgers(self) -> list[TallySupplierLedger]:
        ...

    @abstractmethod
    def list_purchase_vouchers(self, *, from_date: str | None = None) -> list[TallyPurchaseVoucher]:
        ...


class MockTallyReadOnlyConnector(TallyReadOnlyConnector):
    def health(self) -> dict[str, Any]:
        return {"ok": True, "mode": "fixture", "live_tally": False}

    def company_identity(self) -> TallyCompanyIdentity:
        return TallyCompanyIdentity(name="Bharathi Fixture Co", guid="fixture-co-1")

    def list_supplier_ledgers(self) -> list[TallySupplierLedger]:
        return [
            TallySupplierLedger(
                name="Fixture Vendor",
                closing_balance=Decimal("1180.00"),
                guid="led-1",
                gstin="29AAAAA0000A1Z5",
            )
        ]

    def list_purchase_vouchers(self, *, from_date: str | None = None) -> list[TallyPurchaseVoucher]:
        _ = from_date
        return [
            TallyPurchaseVoucher(
                voucher_number="PUR-0001",
                voucher_type="Purchase",
                party_name="Fixture Vendor",
                amount=Decimal("1180.00"),
                voucher_date="2026-04-01",
                tally_guid="mock-guid-purchase-1",
            )
        ]


class UnavailableTallyReadOnlyConnector(TallyReadOnlyConnector):
    def health(self) -> dict[str, Any]:
        return {"ok": False, "mode": "unavailable", "live_tally": False}

    def company_identity(self) -> TallyCompanyIdentity:
        raise TallyReadOnlyError("Tally read-only PoC is not connected")

    def list_supplier_ledgers(self) -> list[TallySupplierLedger]:
        raise TallyReadOnlyError("Tally read-only PoC is not connected")

    def list_purchase_vouchers(self, *, from_date: str | None = None) -> list[TallyPurchaseVoucher]:
        raise TallyReadOnlyError("Tally read-only PoC is not connected")


def parse_tally_ledger_xml(xml_text: str) -> list[TallySupplierLedger]:
    """Parse minimal Tally XML ledger export fixture."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise TallyReadOnlyError("Invalid Tally XML response") from exc
    out: list[TallySupplierLedger] = []
    for led in root.findall(".//LEDGER"):
        name = (led.findtext("NAME") or "").strip()
        bal = led.findtext("CLOSINGBALANCE") or "0"
        try:
            amount = Decimal(str(bal).replace(",", "").strip() or "0")
        except Exception:
            amount = Decimal("0")
        if name:
            out.append(TallySupplierLedger(name=name, closing_balance=amount, guid=led.findtext("GUID")))
    return out


def get_readonly_connector(use_mock: bool = True) -> TallyReadOnlyConnector:
    if use_mock:
        return MockTallyReadOnlyConnector()
    return UnavailableTallyReadOnlyConnector()