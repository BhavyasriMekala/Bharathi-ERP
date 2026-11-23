# Supplier-scoped duplicate detection

## Business key

Duplicates are assessed **per supplier identity**, not globally:

1. `supplier_identity_key` — prefers GSTIN; else normalized supplier name / vendor hint.
2. `invoice_number_norm` — uppercase, stripped invoice number.
3. Tenant scope — same `tenant_id` only.

## Outcomes

| `duplicate_status` | Meaning |
|--------------------|---------|
| `none` | No match |
| `possible_duplicate` | Same supplier + invoice number on another submission |
| `exact_duplicate` | Match on approved (or verifying) submission |

## Approval guard

`approve_submission()` blocks approval when `duplicate_status == exact_duplicate` (database-backed check via `duplicate_detection.py`).

Supervisors may still upload; accountants see flags in the verification queue and register.