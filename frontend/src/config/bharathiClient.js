/** Bharathi client pack — sidebar visibility and labels. */

export const BHARATHI_CLIENT_NAME = "Bharathi Enterprises ERP";

/**
 * Bharathi branding + purchase-invoice pack.
 * When true, Supervisors get a focused nav; Admin and Accountant keep full ERP menus + Bharathi extras.
 */
export const BHARATHI_CLIENT_MODE = import.meta.env.VITE_BHARATHI_CLIENT !== "false";

/** Roles shown on the Bharathi login screen (must match backend demo + RBAC). */
export const BHARATHI_LOGIN_ROLES = ["Admin", "Accountant", "Supervisor", "Store Manager"];

export const BHARATHI_DASHBOARD_PATH = "/bharathi/dashboard";
export const BHARATHI_SUPERVISOR_DASHBOARD_PATH = "/bharathi/bills";

export const BHARATHI_HIDDEN_MODULES = new Set([
  "production",
  "factoryMonitor",
  "iot",
  "hr",
  "quality",
  "maintenance",
  "chat",
  "meetings",
  "analytics",
]);

export const BHARATHI_NAV_EXTRAS = [
  {
    key: "bharathi_dashboard",
    label: "Bharathi Dashboard",
    to: "/bharathi/dashboard",
    module: "dashboard",
  },
  {
    key: "bharathi_bills",
    label: "Scan Invoice",
    to: "/bharathi/bills",
    module: "bharathi_bills",
    icon: null,
  },
  {
    key: "bharathi_register",
    label: "Purchase Invoice Register",
    to: "/bharathi/register",
    module: "bharathi_bills",
  },
  {
    key: "bharathi_suppliers",
    label: "Supplier Invoices",
    to: "/bharathi/suppliers",
    module: "bharathi_bills",
  },
  {
    key: "bharathi_verify",
    label: "Pending Verification",
    to: "/bharathi/verification",
    module: "bharathi_bills",
  },
  {
    key: "bharathi_collections",
    label: "Collections",
    to: "/bharathi/collections",
    module: "bharathi_collections",
  },
  {
    key: "bharathi_tally",
    label: "Tally Sync",
    to: "/bharathi/tally",
    module: "bharathi_tally",
  },
];

/** Supervisor-only: hide non-essential modules and append Bharathi purchase-invoice links. */
export function filterSidebarForBharathiRestricted(items, canSeeModule) {
  const filtered = (items || [])
    .filter((item) => !BHARATHI_HIDDEN_MODULES.has(item.module))
    .map((item) => {
      const children = (item.children || []).filter(
        (c) => !BHARATHI_HIDDEN_MODULES.has(c.module)
      );
      return { ...item, children };
    })
    .filter((item) => canSeeModule(item.module));
  const extras = BHARATHI_NAV_EXTRAS.filter((e) => canSeeModule(e.module));
  return [...filtered, ...extras];
}

/** @deprecated Use filterSidebarForBharathiRestricted — kept for tests importing the old name. */
export const filterSidebarForBharathi = filterSidebarForBharathiRestricted;

/** Admin / Accountant: preserve full ERP sidebar and append Bharathi links (no module stripping). */
export function appendBharathiNavExtras(items, canSeeModule) {
  const base = items || [];
  const seen = new Set();
  for (const section of base) {
    if (section.to) seen.add(section.to);
    for (const child of section.children || []) {
      if (child.to) seen.add(child.to);
    }
  }
  const extras = BHARATHI_NAV_EXTRAS.filter((e) => canSeeModule(e.module) && !seen.has(e.to));
  return extras.length ? [...base, ...extras] : base;
}

/**
 * @param {object} user — from useAuth
 * @param {(mod: string) => boolean} canSeeModule
 */
export function applyBharathiSidebarPolicy(items, user, canSeeModule, { isAdmin, isAccountant, isSupervisor }) {
  if (!BHARATHI_CLIENT_MODE) return items;
  if (isAdmin?.(user) || isAccountant?.(user)) {
    return appendBharathiNavExtras(items, canSeeModule);
  }
  if (isSupervisor?.(user)) {
    return filterSidebarForBharathiRestricted(items, canSeeModule);
  }
  return items;
}