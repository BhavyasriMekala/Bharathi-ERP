/** Bharathi client pack — sidebar visibility and labels. */

export const BHARATHI_CLIENT_NAME = "Bharathi Enterprises ERP";

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
    key: "bharathi_bills",
    label: "Bill Capture",
    to: "/bharathi/bills",
    module: "bharathi_bills",
    icon: null,
  },
  {
    key: "bharathi_verify",
    label: "Verification Queue",
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

export function filterSidebarForBharathi(items, canSeeModule) {
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