import { describe, expect, it } from "vitest";
import { displayGateName, gateLabel } from "@/lib/trading/gate-labels";

const GATE_IDS = [
  "G1",
  "G2",
  "G3",
  "G4",
  "G6",
  "G7",
  "G8",
  "G9",
  "G10",
  "G11",
  "G12",
  "G13",
  "G14",
  "G15",
  "G16",
  "G17",
  "G18",
  "G19",
  "G20",
] as const;

describe("displayGateName", () => {
  it("returns language-map names and never raw G1–G20 ids", () => {
    for (const id of GATE_IDS) {
      const en = displayGateName({ id, name: id }, "en");
      const ar = displayGateName({ id, name: id }, "ar");
      expect(en).toBe(gateLabel(id, "en"));
      expect(ar).toBe(gateLabel(id, "ar"));
      expect(en).not.toMatch(/^G\d+$/i);
      expect(ar).not.toMatch(/^G\d+$/i);
      expect(en.length).toBeGreaterThan(0);
      expect(ar.length).toBeGreaterThan(0);
    }
  });

  it("prefers the language map over a short payload name", () => {
    expect(displayGateName({ id: "G1", name: "News" }, "en")).toBe("News & event shield");
    expect(displayGateName({ id: "G1", name: "News" }, "ar")).toBe("درع الأخبار والأحداث");
  });
});
