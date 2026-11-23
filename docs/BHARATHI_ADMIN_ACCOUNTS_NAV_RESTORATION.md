# Admin & Accounts navigation restoration

Compared **Insights IVA** (read-only reference) vs **Bharathi ERP** on 2026-11-23.

## Root cause

`filterSidebarForBharathi` (under `VITE_BHARATHI_CLIENT=true`) was applied to **all** roles. It stripped non-Bharathi modules (production, HR, analytics, etc.) and replaced Admin/Accountant post-login landing with `/bharathi/dashboard`.

**Pages and routes were not missing** — `sidebarNav.js` and `AppRoutes.jsx` are **byte-identical** to Insights IVA for core ERP structure. Admin (`frontend/src/pages/admin/*`) and Accounts (`frontend/src/pages/accounts/*`, 44 files) are present in Bharathi ERP.

## Fix applied

| Area | Change |
|------|--------|
| `bharathiClient.js` | `applyBharathiSidebarPolicy`: **Admin/Accountant** → `appendBharathiNavExtras` only; **Supervisor** → restricted filter |
| `Sidebar.jsx` | Uses policy helper; imports `isAdmin`, `isSupervisor` |
| `roleRedirect.js` | Admin → `/`; Accountant → `/accounts/dashboard`; Supervisor → `/bharathi/bills` |
| `permissions.js` | Added `isSupervisor()` |

## Comparison matrix (summary)

| Original area | Example route | Admin | Accountant | Bharathi before fix | After fix |
|---------------|---------------|-------|------------|---------------------|-----------|
| ERP dashboard | `/` | Yes | — | Hidden from nav policy | Restored landing |
| Accounts dashboard | `/accounts/dashboard` | — | Yes | Redirect to Bharathi dash | Restored landing |
| Admin users | `/admin/users` | Yes | No | Hidden (sidebar strip) | Visible (Admin) |
| Admin roles | `/admin/roles` | Yes | No | Hidden | Visible |
| Access logs | `/admin/audit-logs` | Yes | No | Hidden | Visible |
| Pending approvals | `/admin/approvals` | Yes | No | Hidden | Visible |
| Finance submenu | `/accounts/*`, `/finance/*` | Yes | Yes | Hidden (Accountant) | Restored |
| Procurement / inventory / sales | various | Yes | partial | Hidden (Accountant) | Per RBAC matrix |
| Bharathi scan | `/bharathi/bills` | Yes | Yes | Extra link | Still appended |
| Bharathi register | `/bharathi/register` | Yes | Yes | Extra link | Still appended |
| Supervisor scan | `/bharathi/bills` | — | — | Yes | Yes (focused nav) |

Full parity: **36** `/admin` + `/accounts` routes in both repos (spot-checked equal).

## Tests

- `bharathiClient.navPolicy.test.js` — Admin/Accountant/Supervisor nav policy
- `sidebarNav.accounts.test.js` — Accounts sidebar (unchanged)
- `npm run build` — run after changes

## Database

No database changes. No Insights IVA modifications.