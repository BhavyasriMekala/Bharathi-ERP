import { describe, expect, it, vi } from "vitest";

import { filterStaticNav } from "../components/layout/Sidebar.jsx";
import { userCanAccess } from "./permissions";
import { applyBharathiSidebarPolicy, BHARATHI_NAV_EXTRAS } from "./bharathiClient";

vi.stubEnv("VITE_BHARATHI_CLIENT", "true");

const adminUser = { role: "Admin", role_name: "Admin", permissions: ["*"] };
const accountantUser = {
  role: "Accountant",
  role_name: "Accountant",
  permissions: [
    "dashboard",
    "accounts",
    "masters",
    "documents",
    "analytics",
    "alerts",
    "settings",
    "sales",
    "bharathi_bills",
    "bharathi_tally",
    "bharathi_collections",
  ],
};
const supervisorUser = {
  role: "Supervisor",
  role_name: "Supervisor",
  permissions: ["dashboard", "bharathi_bills", "documents", "settings"],
};

function wrap(user) {
  const base = filterStaticNav(user);
  return applyBharathiSidebarPolicy(base, user, (mod) => userCanAccess(user, mod), {
    isAdmin: (u) => u.role === "Admin",
    isAccountant: (u) => u.role === "Accountant",
    isSupervisor: (u) => u.role === "Supervisor",
  });
}

describe("Bharathi sidebar policy (production Admin/Accounts)", () => {
  it("Admin keeps admin, finance, and procurement sections plus Bharathi extras", () => {
    const nav = wrap(adminUser);
    expect(nav.some((s) => s.key === "admin")).toBe(true);
    expect(nav.some((s) => s.key === "finance")).toBe(true);
    expect(nav.some((s) => s.key === "procurement")).toBe(true);
    const extras = BHARATHI_NAV_EXTRAS.map((e) => e.to);
    expect(nav.some((s) => extras.includes(s.to))).toBe(true);
  });

  it("Accountant keeps finance masters section and Bharathi verification link", () => {
    const nav = wrap(accountantUser);
    expect(nav.some((s) => s.key === "finance")).toBe(true);
    expect(nav.some((s) => s.to === "/bharathi/verification")).toBe(true);
    expect(nav.some((s) => s.key === "admin")).toBe(false);
  });

  it("Supervisor does not see admin or full finance tree", () => {
    const nav = wrap(supervisorUser);
    expect(nav.some((s) => s.key === "admin")).toBe(false);
    expect(nav.some((s) => s.key === "finance")).toBe(false);
    expect(nav.some((s) => s.to === "/bharathi/bills")).toBe(true);
  });
});