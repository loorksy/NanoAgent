import { describe, expect, test } from "bun:test";

import {
  formatAgreement,
  formatConfidence,
  formatDuration,
  formatNumber,
  formatPercent,
  formatRelative,
  toMillis,
} from "../src/lib/format";

describe("formatNumber", () => {
  test("fixed decimals, signed, and placeholders for missing values", () => {
    expect(formatNumber(2350.5, "en", { decimals: 2 })).toBe("2,350.50");
    expect(formatNumber(3, "en")).toBe("3");
    expect(formatNumber(1.25, "en", { signed: true })).toBe("+1.25");
    expect(formatNumber(null, "en")).toBe("—");
    expect(formatNumber(Number.NaN, "en")).toBe("—");
  });

  test("Arabic locale formats without throwing (digit set depends on the runtime's ICU data)", () => {
    const value = formatNumber(1234.5, "ar", { decimals: 1 });
    expect(value.length).toBeGreaterThan(0);
    expect(value).toMatch(/^[0-9\u0660-\u0669][0-9\u0660-\u0669,\u066B\u066C.]*$/);
  });
});

describe("agreement", () => {
  test("keeps the translated stance beside the counted votes", () => {
    expect(formatAgreement("شراء", 3, 4)).toBe("شراء 3/4");
    expect(formatAgreement("buy", 2, 2)).toBe("buy 2/2");
  });
});

describe("percent / confidence", () => {
  test("percent input is already 0..100", () => {
    expect(formatPercent(12.345, "en")).toBe("12.3%");
    expect(formatPercent(undefined, "en")).toBe("—");
  });

  test("confidence accepts 0..1 and 0..100", () => {
    expect(formatConfidence(0.72, "en")).toBe("72%");
    expect(formatConfidence(72, "en")).toBe("72%");
    expect(formatConfidence(null, "en")).toBe("—");
  });
});

describe("time helpers", () => {
  test("toMillis normalises seconds and milliseconds", () => {
    expect(toMillis(1_700_000_000)).toBe(1_700_000_000_000);
    expect(toMillis(1_700_000_000_000)).toBe(1_700_000_000_000);
    expect(toMillis(null)).toBeNull();
    expect(toMillis(Number.POSITIVE_INFINITY)).toBeNull();
  });

  test("relative time picks the right unit", () => {
    const now = 1_700_000_000_000;
    expect(formatRelative(now + 5 * 60_000, "en", now)).toBe("in 5 minutes");
    expect(formatRelative(now - 3 * 3_600_000, "en", now)).toBe("3 hours ago");
    expect(formatRelative(now - 2 * 86_400_000, "en", now)).toBe("2 days ago");
    expect(formatRelative(undefined, "en", now)).toBe("—");
  });

  test("duration switches to seconds past 1000 ms", () => {
    expect(formatDuration(250, "en")).toBe("250 ms");
    expect(formatDuration(1500, "en")).toBe("1.5 s");
    expect(formatDuration(null, "en")).toBe("");
  });
});
