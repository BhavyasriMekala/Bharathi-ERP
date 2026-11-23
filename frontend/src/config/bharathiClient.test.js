import { describe, expect, it } from "vitest";

import { BHARATHI_HIDDEN_MODULES, BHARATHI_LOGIN_ROLES } from "./bharathiClient";

describe("Bharathi login roles", () => {
  it("exposes Admin, Accountant, Supervisor, and Store Manager", () => {
    expect(BHARATHI_LOGIN_ROLES).toEqual([
      "Admin",
      "Accountant",
      "Supervisor",
      "Store Manager",
    ]);
  });

  it("keeps inventory visible for Store Manager (not in hidden modules)", () => {
    expect(BHARATHI_HIDDEN_MODULES.has("inventory")).toBe(false);
    expect(BHARATHI_HIDDEN_MODULES.has("procurement")).toBe(false);
  });
});