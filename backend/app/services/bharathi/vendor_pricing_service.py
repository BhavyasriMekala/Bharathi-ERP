"""Vendor quotation / last-purchase comparison (landed cost aware)."""

from __future__ import annotations

from decimal import Decimal


def normalize_uom(uom: str | None) -> str:
    u = (uom or "").strip().lower()
    aliases = {"nos": "ea", "pcs": "ea", "piece": "ea", "pieces": "ea"}
    return aliases.get(u, u or "ea")


def comparable_landed_cost(
    unit_price: Decimal,
    qty: Decimal,
    gst_pct: Decimal,
    freight: Decimal = Decimal("0"),
    *,
    gst_inclusive: bool = False,
) -> Decimal:
    if qty <= 0:
        return Decimal("0")
    base = unit_price * qty
    if not gst_inclusive:
        base = base * (Decimal("1") + (gst_pct / Decimal("100")))
    return (base + freight) / qty


def compare_vendor_rows(rows: list[dict]) -> list[dict]:
    """Group by material_key + uom; flag incomparable spec/unit mismatches."""
    by_key: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row.get("material_key") or "").strip().lower()
        uom = normalize_uom(row.get("uom"))
        by_key.setdefault((key, uom), []).append(row)
    out = []
    for (mat, uom), group in by_key.items():
        landed = []
        for g in group:
            try:
                lc = comparable_landed_cost(
                    Decimal(str(g.get("unit_price") or 0)),
                    Decimal(str(g.get("quantity") or 1)),
                    Decimal(str(g.get("gst_pct") or 0)),
                    Decimal(str(g.get("freight") or 0)),
                    gst_inclusive=bool(g.get("gst_inclusive")),
                )
            except Exception:
                continue
            landed.append({**g, "landed_unit_cost": float(lc)})
        if not landed:
            continue
        best = min(landed, key=lambda x: x["landed_unit_cost"])
        out.append(
            {
                "material_key": mat,
                "uom": uom,
                "suggested_vendor": best.get("vendor_name"),
                "lowest_landed_cost": best["landed_unit_cost"],
                "comparisons": landed,
            }
        )
    return out