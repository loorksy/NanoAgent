import type { LogEntry, Mt5Permissions, ResultRecord } from "@nanoagent/sdk";
import { describe, expect, test } from "bun:test";

import { t } from "../src/i18n";
import { describeLogEntry, logEntryKey, logTone } from "../src/lib/log";
import { expiryFromHours, formatRiskValue, widensAuthority } from "../src/lib/risk";
import { isStructuredType, toStructuredResult } from "../src/lib/results";
import { colors } from "../src/lib/theme";

const translate = (key: string, params?: Record<string, unknown>) => t(key, params as never, "en");

const GRANT: Mt5Permissions = {
  level: "propose",
  can_open: false,
  can_modify_sl_tp: true,
  allow_widen_stop: false,
  can_partial_close: true,
  can_close_all: false,
  can_place_pending: false,
  max_lot_per_order: null,
  max_total_lots: null,
  auto_daily_loss_pct: null,
  sessions: ["london", "newyork"],
  news_lock: true,
  expires_at: 1_800_000_000,
  grace_hours: 2,
  granted_at: 1_700_000_000,
  granted_by: "owner",
};

describe("risk helpers", () => {
  test("formatRiskValue picks the unit template", () => {
    expect(formatRiskValue({ name: "risk_pct_default", unit: "%", type: "number" }, 0.5, translate, "en")).toBe("0.50%");
    expect(formatRiskValue({ name: "news_shield_minutes", unit: "min", type: "integer" }, 30, translate, "en")).toBe("30 min");
    expect(formatRiskValue({ name: "spread_max_points", unit: "pts", type: "integer" }, 45, translate, "en")).toBe("45 pts");
    expect(formatRiskValue({ name: "min_rr", unit: "x", type: "number" }, 1.5, translate, "en")).toBe("1:1.5");
    expect(formatRiskValue({ name: "max_open_gold_positions", unit: "", type: "integer" }, 2, translate, "en")).toBe("2");
  });

  test("expiryFromHours returns epoch seconds or null", () => {
    const now = 1_700_000_000_000;
    expect(expiryFromHours(24, now)).toBe(1_700_000_000 + 86_400);
    expect(expiryFromHours(null, now)).toBeNull();
  });

  test("widensAuthority flags level raises, new capabilities, lock removal and expiry removal", () => {
    expect(widensAuthority(GRANT, GRANT)).toBe(false);
    expect(widensAuthority(GRANT, { ...GRANT, level: "execute" })).toBe(true);
    expect(widensAuthority(GRANT, { ...GRANT, level: "recommend" })).toBe(false);
    expect(widensAuthority(GRANT, { ...GRANT, can_open: true })).toBe(true);
    expect(widensAuthority(GRANT, { ...GRANT, can_modify_sl_tp: false })).toBe(false);
    expect(widensAuthority(GRANT, { ...GRANT, news_lock: false })).toBe(true);
    expect(widensAuthority(GRANT, { ...GRANT, expires_at: null })).toBe(true);
    expect(widensAuthority(GRANT, { ...GRANT, sessions: ["asia"] })).toBe(false);
  });
});

function entry(kind: LogEntry["kind"], data: Record<string, unknown>, id = ""): LogEntry {
  return { id, ts: 1_700_000_000_000, kind, source: "gateway", data };
}

describe("log helpers", () => {
  test("keys fall back to kind + ts + index when the gateway id is empty", () => {
    expect(logEntryKey(entry("decision", {}), 3)).toBe("decision-1700000000000-3");
    expect(logEntryKey(entry("approval", {}, "01H"), 0)).toBe("01H");
  });

  test("tone reflects outcome", () => {
    expect(logTone(entry("gate", {}))).toBe(colors.warning);
    expect(logTone(entry("execution", { event: "failed" }))).toBe(colors.danger);
    expect(logTone(entry("execution", { event: "finished" }))).toBe(colors.success);
    expect(logTone(entry("approval", { status: "confirmed" }))).toBe(colors.success);
    expect(logTone(entry("approval", { status: "expired" }))).toBe(colors.danger);
    expect(logTone(entry("decision", { verdict: "sell" }))).toBe(colors.sell);
    expect(logTone(entry("permission", {}))).toBe(colors.accent);
  });

  test("describe resolves label keys and keeps free text", () => {
    const label = (key: string, params?: Record<string, unknown>) => translate(key, params);
    expect(describeLogEntry(entry("execution", { name: "mt5_place_order", event: "finished", summary: "0.10 lot" }), label)).toEqual({
      title: "mt5_place_order · Finished",
      detail: "0.10 lot",
    });
    expect(describeLogEntry(entry("approval", { type: "execution", status: "confirmed", summary: "Buy XAUUSD" }), label)).toEqual({
      title: "Execution",
      detail: "Confirmed · Buy XAUUSD",
    });
    expect(describeLogEntry(entry("notification", { title: "tabs.agent", body: "tasks.next_run", args: { when: "soon" } }), label)).toEqual({
      title: "Agent",
      detail: "Next run soon",
    });
    expect(describeLogEntry(entry("structured", { type: "decision", payload: { verdict: "buy" } }), label)).toEqual({ title: "Decision", detail: "buy" });
    expect(describeLogEntry(entry("decision", { symbol: "XAUUSD", direction: "buy", reason: "sweep" }), label)).toEqual({
      title: "XAUUSD · buy",
      detail: "sweep",
    });
    expect(describeLogEntry(entry("permission", { who: "owner", changes: { level: "execute", can_open: true } }), label)).toEqual({
      title: "Granted by owner",
      detail: "Level: execute · Open positions: true",
    });
    expect(describeLogEntry(entry("job", { job_id: "j1", status: "finished" }), label)).toEqual({ title: "j1", detail: "Finished" });
  });
});

describe("results helpers", () => {
  test("toStructuredResult narrows a REST record", () => {
    const record: ResultRecord = { id: "res_1", session: "s1", run: "r1", type: "decision", ts: 5, payload: { verdict: "wait" } };
    expect(toStructuredResult(record)).toEqual({ type: "decision", result_id: "res_1", payload: { verdict: "wait" }, ts: 5, session: "s1" });
    expect(toStructuredResult({ ...record, session: null })).not.toHaveProperty("session");
    expect(isStructuredType("scorecard")).toBe(true);
    expect(isStructuredType("weather")).toBe(false);
  });
});
