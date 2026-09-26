import type { PairDeviceResponse, Scope } from "@nanoagent/sdk";
import { createStore } from "zustand/vanilla";

import { isLocale, setLocale, type Locale } from "../i18n";
import type { KeyValueStore } from "../lib/storage";

export const STORAGE_KEYS = {
  gatewayUrl: "nanoagent.gateway_url",
  token: "nanoagent.device_token",
  clientId: "nanoagent.client_id",
  deviceId: "nanoagent.device_id",
  scopes: "nanoagent.scopes",
  locale: "nanoagent.locale",
  pushToken: "nanoagent.push_token",
  pushPlatform: "nanoagent.push_platform",
} as const;

export type PushPlatform = "ios" | "android";

export interface AuthState {
  hydrated: boolean;
  gatewayUrl: string | undefined;
  token: string | undefined;
  clientId: string | undefined;
  deviceId: string | undefined;
  scopes: Scope[];
  locale: Locale;
  pushToken: string | undefined;
  pushPlatform: PushPlatform | undefined;
}

export interface AuthActions {
  hydrate(): Promise<void>;
  /** Persist the result of `POST /devices/pair`. */
  pair(gatewayUrl: string, response: PairDeviceResponse): Promise<void>;
  setLocale(locale: Locale): Promise<void>;
  setPushRegistration(platform: PushPlatform, pushToken: string, deviceId: string): Promise<void>;
  clearPushRegistration(): Promise<void>;
  unpair(): Promise<void>;
  hasScope(scope: Scope): boolean;
}

export type AuthStore = AuthState & AuthActions;

const EMPTY: AuthState = {
  hydrated: false,
  gatewayUrl: undefined,
  token: undefined,
  clientId: undefined,
  deviceId: undefined,
  scopes: [],
  locale: "en",
  pushToken: undefined,
  pushPlatform: undefined,
};

function parseScopes(raw: string | null): Scope[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((item): item is Scope => typeof item === "string") : [];
  } catch {
    return [];
  }
}

export function isPaired(state: Pick<AuthState, "gatewayUrl" | "token">): boolean {
  return Boolean(state.gatewayUrl && state.token);
}

export function createAuthStore(storage: KeyValueStore, options: { deviceLocale?: string } = {}) {
  return createStore<AuthStore>()((set, get) => ({
    ...EMPTY,

    async hydrate() {
      const [gatewayUrl, token, clientId, deviceId, scopes, locale, pushToken, pushPlatform] = await Promise.all([
        storage.get(STORAGE_KEYS.gatewayUrl),
        storage.get(STORAGE_KEYS.token),
        storage.get(STORAGE_KEYS.clientId),
        storage.get(STORAGE_KEYS.deviceId),
        storage.get(STORAGE_KEYS.scopes),
        storage.get(STORAGE_KEYS.locale),
        storage.get(STORAGE_KEYS.pushToken),
        storage.get(STORAGE_KEYS.pushPlatform),
      ]);
      const deviceLocale = options.deviceLocale?.slice(0, 2).toLowerCase();
      const resolvedLocale: Locale = isLocale(locale) ? locale : isLocale(deviceLocale) ? deviceLocale : "en";
      setLocale(resolvedLocale);
      set({
        hydrated: true,
        gatewayUrl: gatewayUrl ?? undefined,
        token: token ?? undefined,
        clientId: clientId ?? undefined,
        deviceId: deviceId ?? undefined,
        scopes: parseScopes(scopes),
        locale: resolvedLocale,
        pushToken: pushToken ?? undefined,
        pushPlatform: pushPlatform === "ios" || pushPlatform === "android" ? pushPlatform : undefined,
      });
    },

    async pair(gatewayUrl, response) {
      const scopes = response.client.scopes;
      await Promise.all([
        storage.set(STORAGE_KEYS.gatewayUrl, gatewayUrl),
        storage.set(STORAGE_KEYS.token, response.token),
        storage.set(STORAGE_KEYS.clientId, response.client.id),
        storage.set(STORAGE_KEYS.scopes, JSON.stringify(scopes)),
        response.device ? storage.set(STORAGE_KEYS.deviceId, response.device.id) : Promise.resolve(),
      ]);
      set({
        gatewayUrl,
        token: response.token,
        clientId: response.client.id,
        scopes,
        deviceId: response.device?.id ?? get().deviceId,
      });
    },

    async setLocale(locale) {
      await storage.set(STORAGE_KEYS.locale, locale);
      setLocale(locale);
      set({ locale });
    },

    async setPushRegistration(platform, pushToken, deviceId) {
      await Promise.all([
        storage.set(STORAGE_KEYS.pushToken, pushToken),
        storage.set(STORAGE_KEYS.pushPlatform, platform),
        storage.set(STORAGE_KEYS.deviceId, deviceId),
      ]);
      set({ pushPlatform: platform, pushToken, deviceId });
    },

    async clearPushRegistration() {
      await Promise.all([
        storage.remove(STORAGE_KEYS.pushToken),
        storage.remove(STORAGE_KEYS.pushPlatform),
        storage.remove(STORAGE_KEYS.deviceId),
      ]);
      set({ pushPlatform: undefined, pushToken: undefined, deviceId: undefined });
    },

    async unpair() {
      const { locale } = get();
      await Promise.all(
        Object.values(STORAGE_KEYS)
          .filter((key) => key !== STORAGE_KEYS.locale)
          .map((key) => storage.remove(key)),
      );
      set({ ...EMPTY, hydrated: true, locale });
    },

    hasScope(scope) {
      const { scopes } = get();
      return scopes.includes(scope) || scopes.includes("admin");
    },
  }));
}

export type AuthStoreApi = ReturnType<typeof createAuthStore>;
