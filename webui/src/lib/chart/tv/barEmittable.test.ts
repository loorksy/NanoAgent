import { describe, expect, it } from "vitest";
import { barEmittable } from "./tvDatafeed";

describe("barEmittable", () => {
  it("allows first bar and updates at same time", () => {
    expect(barEmittable(undefined, 1_000)).toBe(true);
    expect(barEmittable(1_000, 1_000)).toBe(true);
  });

  it("rejects backwards bar times", () => {
    expect(barEmittable(2_000, 1_000)).toBe(false);
  });

  it("allows forward bar times", () => {
    expect(barEmittable(1_000, 2_000)).toBe(true);
  });
});
