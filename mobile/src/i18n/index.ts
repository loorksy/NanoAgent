import ar from "./ar.json";
import en from "./en.json";

export type Locale = "en" | "ar";

export const LOCALES: readonly Locale[] = ["en", "ar"] as const;

type Catalog = Record<string, string>;

const catalogs: Record<Locale, Catalog> = { en, ar };

let current: Locale = "en";
const listeners = new Set<(locale: Locale) => void>();

export function isLocale(value: string | null | undefined): value is Locale {
  return value === "en" || value === "ar";
}

export function getLocale(): Locale {
  return current;
}

export function setLocale(locale: Locale): void {
  if (locale === current) return;
  current = locale;
  for (const listener of listeners) listener(locale);
}

export function onLocaleChange(listener: (locale: Locale) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function isRTL(locale: Locale = current): boolean {
  return locale === "ar";
}

export type Params = Record<string, string | number | boolean | null | undefined>;

function interpolate(template: string, params: Params | undefined): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = params[name];
    return value === undefined || value === null ? match : String(value);
  });
}

/** Translate `key` in the active locale, falling back to English and then the key itself. */
export function t(key: string, params?: Params, locale: Locale = current): string {
  const template = catalogs[locale][key] ?? catalogs.en[key] ?? key;
  return interpolate(template, params);
}

export function hasKey(key: string, locale: Locale = current): boolean {
  return key in catalogs[locale] || key in catalogs.en;
}

/**
 * Resolve a gateway label key: the server catalog (`GET /labels?locale=`) wins, then the local
 * catalog, then the raw key so nothing is ever silently hidden.
 */
export function label(key: string, serverLabels?: Record<string, string> | null, params?: Params): string {
  const fromServer = serverLabels?.[key];
  if (fromServer) return interpolate(fromServer, params);
  return t(key, params);
}

export function missingKeys(locale: Locale): string[] {
  return Object.keys(catalogs.en).filter((key) => !(key in catalogs[locale]));
}
