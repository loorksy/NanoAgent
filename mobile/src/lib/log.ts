import type { LogEntry } from "@nanoagent/sdk";

import type { Params } from "../i18n";
import { colors } from "./theme";

type Resolve = (key: string, params?: Params) => string;

function text(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return undefined;
}

function firstText(data: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const found = text(data[key]);
    if (found) return found;
  }
  return undefined;
}

/** Stable list key: gateway rows carry a ULID, decision/permission rows may not. */
export function logEntryKey(entry: LogEntry, index: number): string {
  return entry.id || `${entry.kind}-${entry.ts}-${index}`;
}

export function logTone(entry: LogEntry): string {
  const data = entry.data;
  switch (entry.kind) {
    case "gate":
      return colors.warning;
    case "execution":
      return data["event"] === "failed" ? colors.danger : colors.success;
    case "approval": {
      const status = data["status"];
      if (status === "confirmed" || status === "auto_confirmed") return colors.success;
      if (status === "cancelled" || status === "expired") return colors.danger;
      return colors.warning;
    }
    case "job": {
      const status = data["status"];
      if (status === "failed" || status === "error") return colors.danger;
      if (status === "finished") return colors.success;
      return colors.info;
    }
    case "notification": {
      const level = data["level"];
      if (level === "error") return colors.danger;
      if (level === "warning") return colors.warning;
      return colors.info;
    }
    case "decision": {
      const verdict = String(data["verdict"] ?? data["direction"] ?? data["action"] ?? "").toLowerCase();
      if (verdict.includes("buy") || verdict.includes("long")) return colors.buy;
      if (verdict.includes("sell") || verdict.includes("short")) return colors.sell;
      return colors.wait;
    }
    case "permission":
      return colors.accent;
    case "structured":
    default:
      return colors.textMuted;
  }
}

/**
 * Title + detail for one operator-log row. Label keys carried by the gateway (`title`,
 * `body`, `reason_key`) go through the label resolver; free-text summaries are shown as-is.
 */
export function describeLogEntry(entry: LogEntry, label: Resolve): { title: string; detail?: string } {
  const data = entry.data;
  switch (entry.kind) {
    case "execution":
    case "gate": {
      const name = firstText(data, ["name"]) ?? label("log.kind.execution");
      const summary = firstText(data, ["summary"]);
      const phase = text(data["event"]);
      const title = phase ? `${name} · ${label(`timeline.${phase === "started" ? "running" : phase}`)}` : name;
      return summary ? { title, detail: summary } : { title };
    }
    case "approval": {
      const type = text(data["type"]);
      const status = text(data["status"]);
      const title = type ? label(`approval.type.${type}`) : label("log.kind.approval");
      const parts = [status ? label(`approval.status.${status}`) : undefined, firstText(data, ["summary"])].filter(Boolean);
      return parts.length ? { title, detail: parts.join(" · ") } : { title };
    }
    case "job": {
      const title = firstText(data, ["name", "job_id"]) ?? label("log.kind.job");
      const status = text(data["status"]);
      return status ? { title, detail: label(`job.status.${status}`) } : { title };
    }
    case "notification": {
      const args = (data["args"] as Params | undefined) ?? undefined;
      const titleKey = text(data["title"]);
      const bodyKey = text(data["body"]);
      const title = titleKey ? label(titleKey, args) : label("log.kind.notification");
      return bodyKey ? { title, detail: label(bodyKey, args) } : { title };
    }
    case "structured": {
      const type = text(data["type"]);
      const title = type ? label(`card.${type}.title`) : label("log.kind.structured");
      const payload = data["payload"] as Record<string, unknown> | undefined;
      const detail = payload ? firstText(payload, ["verdict", "state", "htf_bias", "summary"]) : undefined;
      return detail ? { title, detail } : { title };
    }
    case "decision": {
      const symbol = firstText(data, ["symbol", "instrument"]);
      const verdict = firstText(data, ["verdict", "direction", "action", "decision"]);
      const title = [symbol, verdict].filter(Boolean).join(" · ") || label("log.kind.decision");
      const detail = firstText(data, ["summary", "reason", "reasons", "note", "rationale"]);
      return detail ? { title, detail } : { title };
    }
    case "permission": {
      const who = firstText(data, ["who", "granted_by"]);
      const title = who ? label("mt5.granted_by", { who }) : label("log.kind.permission");
      const changes = data["changes"];
      const detail =
        changes && typeof changes === "object"
          ? Object.entries(changes as Record<string, unknown>)
              .map(([key, value]) => `${label(`mt5.${key}`)}: ${typeof value === "object" && value !== null ? JSON.stringify(value) : String(value)}`)
              .join(" · ")
          : firstText(data, ["action", "summary", "level"]);
      return detail ? { title, detail } : { title };
    }
    default:
      return { title: entry.kind };
  }
}
