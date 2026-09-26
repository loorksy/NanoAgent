import { describe, expect, test } from "bun:test";

import ar from "../src/i18n/ar.json";
import en from "../src/i18n/en.json";
import { LOCALES, isRTL, label, missingKeys, setLocale, t } from "../src/i18n";

const PLACEHOLDER = /\{(\w+)\}/g;

function placeholders(template: string): string[] {
  return [...template.matchAll(PLACEHOLDER)].map((match) => match[1] ?? "").sort();
}

describe("catalog parity", () => {
  test("every English key exists in Arabic and vice versa", () => {
    expect(missingKeys("ar")).toEqual([]);
    expect(Object.keys(ar).filter((key) => !(key in en))).toEqual([]);
  });

  test("placeholders match across locales", () => {
    for (const [key, template] of Object.entries(en)) {
      expect({ key, placeholders: placeholders((ar as Record<string, string>)[key] ?? "") }).toEqual({
        key,
        placeholders: placeholders(template),
      });
    }
  });

  test("no empty values", () => {
    for (const catalog of [en, ar]) {
      for (const [key, value] of Object.entries(catalog)) {
        expect({ key, empty: value.trim().length === 0 }).toEqual({ key, empty: false });
      }
    }
  });
});

describe("t()", () => {
  test("interpolates params and keeps unknown placeholders", () => {
    expect(t("tasks.next_run", { when: "soon" }, "en")).toBe("Next run soon");
    expect(t("timeline.show", {}, "en")).toBe("Show {count} steps");
  });

  test("falls back to English then to the key", () => {
    expect(t("nope.missing", undefined, "ar")).toBe("nope.missing");
    expect(t("tabs.agent", undefined, "ar")).toBe((ar as Record<string, string>)["tabs.agent"]);
  });

  test("locale switching notifies and drives RTL", () => {
    expect(LOCALES).toEqual(["en", "ar"]);
    setLocale("ar");
    expect(isRTL()).toBe(true);
    expect(t("tabs.agent")).toBe((ar as Record<string, string>)["tabs.agent"]);
    setLocale("en");
    expect(isRTL()).toBe(false);
  });
});

describe("label()", () => {
  test("server catalog wins over the bundled one", () => {
    expect(label("tabs.agent", { "tabs.agent": "Bot" })).toBe("Bot");
    expect(label("tabs.agent", {})).toBe("Agent");
    expect(label("push.job.title", null, { job_id: "x" })).toBe("push.job.title");
  });
});
