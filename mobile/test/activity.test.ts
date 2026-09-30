import { describe, expect, test } from "bun:test";

import { t } from "../src/i18n";
import { workingBadgeCopy } from "../src/lib/activity";

const translate = (key: string) => t(key, undefined, "en");
const lookup = (key: string) => key;

describe("workingBadgeCopy", () => {
  test("a run in progress does not claim a reply or a tool", () => {
    expect(workingBadgeCopy("streaming", translate, lookup)).toEqual({
      title: "Processing",
      detail: "",
    });
    expect(workingBadgeCopy("tool:get_gold_quote", translate, lookup)).toEqual({
      title: "Processing",
      detail: "",
    });
    expect(workingBadgeCopy("thinking", translate, lookup).detail).toBe("");
    expect(workingBadgeCopy(undefined, translate, lookup).title).toBe("Processing");
  });

  test("a queued turn keeps the queue phase", () => {
    const copy = workingBadgeCopy("queued", translate, (key) =>
      key === "phase.queued" ? "Queued" : key,
    );
    expect(copy).toEqual({ title: "Working", detail: "Queued" });
  });

  test("a server processing phrase wins", () => {
    const copy = workingBadgeCopy("streaming", translate, (key) =>
      key === "state.processing" ? "جاري المعالجة…" : key,
    );
    expect(copy.title).toBe("جاري المعالجة…");
  });
});
