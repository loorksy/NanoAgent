import { describe, expect, test } from "bun:test";

import { t } from "../src/i18n";
import { timelineDetail, workingBadgeCopy } from "../src/lib/activity";

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

  test("thinking is shown only when the provider sent that signal", () => {
    expect(workingBadgeCopy("thinking", translate, lookup, true)).toEqual({
      title: "Working",
      detail: "Thinking",
    });
    const arabic = workingBadgeCopy(
      "thinking",
      (key) => (key === "state.working" ? "يعمل" : "يفكّر"),
      (key) => (key === "phase.thinking" ? "يفكّر" : key),
      true,
    );
    expect(arabic).toEqual({ title: "يعمل", detail: "يفكّر" });
  });

  test("a queued turn keeps the queue phase", () => {
    const copy = workingBadgeCopy("queued", translate, (key) =>
      key === "phase.queued" ? "Queued" : key,
    );
    expect(copy).toEqual({ title: "Working", detail: "Queued" });
  });

  test("an expanded tool row keeps inputs and the result from the same call", () => {
    expect(
      timelineDetail({
        id: "1",
        kind: "tool",
        call_id: "c1",
        name: "get_gold_quote",
        status: "finished",
        started_at: 1,
        arguments: "{\"symbol\":\"XAUUSD\"}",
        summary: "bid 2401",
        duration_ms: 200,
      }),
    ).toBe("get_gold_quote · {\"symbol\":\"XAUUSD\"} · bid 2401");
    expect(
      timelineDetail({
        id: "2",
        kind: "tool",
        call_id: "c2",
        name: "get_gate_report",
        status: "failed",
        started_at: 1,
        summary: "feed down",
      }),
    ).toBe("get_gate_report · feed down");
  });

  test("a server processing phrase wins", () => {
    const copy = workingBadgeCopy("streaming", translate, (key) =>
      key === "state.processing" ? "جاري المعالجة…" : key,
    );
    expect(copy.title).toBe("جاري المعالجة…");
  });
});
