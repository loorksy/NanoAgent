import type { Locale } from "../i18n";

const LOCALE_TAG: Record<Locale, string> = { en: "en-US", ar: "ar" };

function tag(locale: Locale): string {
  return LOCALE_TAG[locale];
}

/** Prices and levels: fixed decimals, locale digits. */
export function formatNumber(
  value: number | null | undefined,
  locale: Locale,
  options: { decimals?: number; signed?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const decimals = options.decimals ?? (Number.isInteger(value) ? 0 : 2);
  const formatted = new Intl.NumberFormat(tag(locale), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
  return options.signed && value > 0 ? `+${formatted}` : formatted;
}

export function formatPercent(value: number | null | undefined, locale: Locale, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(tag(locale), {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/** Catalog label for a gate id. A missing label keeps the id. */
export function gateCaption(resolve: (key: string) => string, gate: string): string {
  const key = `label.gate.${gate}`;
  const named = resolve(key);
  return named === key ? gate : named;
}

/** Stance word already translated, then the counted votes. */
export function formatAgreement(stanceLabel: string, agreeing: number, votes: number): string {
  return `${stanceLabel} ${agreeing}/${votes}`;
}

/** 0..1 confidence to a percentage label. */
export function formatConfidence(value: number | null | undefined, locale: Locale): string {
  if (value === null || value === undefined) return "—";
  const pct = value <= 1 ? value * 100 : value;
  return formatPercent(pct, locale, 0);
}

export function formatTime(ts: number | null | undefined, locale: Locale): string {
  if (!ts) return "—";
  return new Intl.DateTimeFormat(tag(locale), { hour: "2-digit", minute: "2-digit" }).format(new Date(ts));
}

export function formatDateTime(ts: number | null | undefined, locale: Locale): string {
  if (!ts) return "—";
  return new Intl.DateTimeFormat(tag(locale), {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(ts));
}

/** Relative time without pulling a library: "in 5 min", "3 h ago". */
export function formatRelative(ts: number | null | undefined, locale: Locale, now = Date.now()): string {
  if (!ts) return "—";
  const rtf = new Intl.RelativeTimeFormat(tag(locale), { numeric: "auto" });
  const diffSeconds = Math.round((ts - now) / 1000);
  const abs = Math.abs(diffSeconds);
  if (abs < 60) return rtf.format(diffSeconds, "second");
  if (abs < 3600) return rtf.format(Math.round(diffSeconds / 60), "minute");
  if (abs < 86_400) return rtf.format(Math.round(diffSeconds / 3600), "hour");
  return rtf.format(Math.round(diffSeconds / 86_400), "day");
}

export function formatDuration(ms: number | null | undefined, locale: Locale): string {
  if (ms === null || ms === undefined) return "";
  if (ms < 1000) return `${formatNumber(ms, locale, { decimals: 0 })} ms`;
  return `${formatNumber(ms / 1000, locale, { decimals: 1 })} s`;
}

/** Normalise the gateway's epoch values (seconds or milliseconds) to milliseconds. */
export function toMillis(value: number | null | undefined): number | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  return value < 1e12 ? value * 1000 : value;
}
