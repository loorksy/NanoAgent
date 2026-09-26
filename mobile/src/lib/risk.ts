import type { Mt5Permissions, PermissionLevel, RiskFieldDescriptor } from "@nanoagent/sdk";

import type { Locale, Params } from "../i18n";
import { formatNumber } from "./format";

export const PERMISSION_LEVELS: readonly PermissionLevel[] = ["recommend", "propose", "execute"] as const;

const LEVEL_RANK: Record<PermissionLevel, number> = { recommend: 0, propose: 1, execute: 2 };

/** Flags that widen what the agent may do on MT5 (08 §3); relaxing any of them needs a local gate. */
export const MT5_CAPABILITY_FLAGS: readonly (keyof Mt5Permissions)[] = [
  "can_open",
  "can_modify_sl_tp",
  "allow_widen_stop",
  "can_partial_close",
  "can_close_all",
  "can_place_pending",
] as const;

/** Unit-aware slider label; the gateway's `unit` is a short code (`%`, `min`, `pts`, `x`, ...). */
export function formatRiskValue(
  field: Pick<RiskFieldDescriptor, "unit" | "type" | "name">,
  value: number,
  t: (key: string, params?: Params) => string,
  locale: Locale,
): string {
  const decimals = field.type === "integer" ? 0 : field.name === "min_rr" ? 1 : 2;
  const number = formatNumber(value, locale, { decimals });
  const unit = field.unit.toLowerCase();
  if (unit === "%" || unit === "pct" || unit === "percent") return t("risk.unit.pct", { value: number });
  if (unit === "min" || unit === "minutes") return t("risk.unit.minutes", { value: number });
  if (unit === "h" || unit === "hours") return t("risk.unit.hours", { value: number });
  if (unit === "pts" || unit === "points") return t("risk.unit.points", { value: number });
  if (unit === "rr" || unit === "x" || field.name === "min_rr") return t("risk.unit.rr", { value: number });
  return t("risk.unit.count", { value: number });
}

/** Expiry timestamp (epoch seconds) for a grant that lasts `hours`; `null` means no expiry. */
export function expiryFromHours(hours: number | null, now = Date.now()): number | null {
  return hours === null ? null : Math.floor(now / 1000) + hours * 3600;
}

/**
 * Whether moving from `current` to `next` widens the agent's authority: a higher level, a
 * capability switched on, or the news lock switched off. Such changes must pass the
 * biometric gate before `PUT /connect/mt5/permissions` (05 §4).
 */
export function widensAuthority(current: Mt5Permissions, next: Mt5Permissions): boolean {
  if (LEVEL_RANK[next.level] > LEVEL_RANK[current.level]) return true;
  if (current.news_lock && !next.news_lock) return true;
  if (current.expires_at !== null && next.expires_at === null) return true;
  return MT5_CAPABILITY_FLAGS.some((flag) => next[flag] === true && current[flag] === false);
}
