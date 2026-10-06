import { GatewayClient } from "@mokli/sdk";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useStore } from "zustand";

import { getLocale, onLocaleChange, t as translate, type Locale, type Params } from "../i18n";
import { createAuthStore, type AuthStore, type AuthStoreApi } from "../stores/auth";
import { createLabelsStore, type LabelsStore, type LabelsStoreApi } from "../stores/labels";
import { createInboxStore, type InboxStore, type InboxStoreApi } from "../stores/notifications";
import type { KeyValueStore } from "./storage";

export interface AppStores {
  auth: AuthStoreApi;
  inbox: InboxStoreApi;
  labels: LabelsStoreApi;
}

const AppContext = createContext<AppStores | undefined>(undefined);

export function createAppStores(storage: KeyValueStore, deviceLocale?: string): AppStores {
  return {
    auth: createAuthStore(storage, deviceLocale ? { deviceLocale } : {}),
    inbox: createInboxStore(storage),
    labels: createLabelsStore(),
  };
}

export function AppProvider({ stores, children }: { stores: AppStores; children: ReactNode }) {
  return <AppContext.Provider value={stores}>{children}</AppContext.Provider>;
}

export function useStores(): AppStores {
  const stores = useContext(AppContext);
  if (!stores) throw new Error("AppProvider missing");
  return stores;
}

export function useAuth<T = AuthStore>(selector: (state: AuthStore) => T = (state) => state as unknown as T): T {
  return useStore(useStores().auth, selector);
}

export function useInbox<T = InboxStore>(selector: (state: InboxStore) => T = (state) => state as unknown as T): T {
  return useStore(useStores().inbox, selector);
}

export function useLabelsStore<T = LabelsStore>(
  selector: (state: LabelsStore) => T = (state) => state as unknown as T,
): T {
  return useStore(useStores().labels, selector);
}

/** Active locale as React state (re-renders on change). */
export function useLocale(): Locale {
  const [locale, setLocaleState] = useState<Locale>(getLocale());
  useEffect(() => onLocaleChange(setLocaleState), []);
  return locale;
}

/** Bundled translation bound to the active locale. */
export function useT(): (key: string, params?: Params) => string {
  const locale = useLocale();
  return useMemo(() => (key: string, params?: Params) => translate(key, params, locale), [locale]);
}

/** Gateway label (server catalog → bundled → key). */
export function useLabel(): (key: string, params?: Params) => string {
  const locale = useLocale();
  const catalog = useLabelsStore((state) => state.catalogs[locale]);
  const resolve = useLabelsStore((state) => state.resolve);
  return useMemo(() => (key: string, params?: Params) => resolve(key, locale, params), [resolve, locale, catalog]);
}

/** One GatewayClient per gateway URL; the token is read lazily so re-pairing needs no new client. */
export function useClient(): GatewayClient | undefined {
  const { auth } = useStores();
  const gatewayUrl = useAuth((state) => state.gatewayUrl);
  const locale = useLocale();
  const client = useMemo(() => {
    if (!gatewayUrl) return undefined;
    return new GatewayClient({ baseUrl: gatewayUrl, token: () => auth.getState().token, locale });
  }, [auth, gatewayUrl, locale]);
  useEffect(() => {
    if (client) client.locale = locale;
  }, [client, locale]);
  return client;
}

/** Client that must exist (screens behind the pairing gate). */
export function useRequiredClient(): GatewayClient {
  const client = useClient();
  if (!client) throw new Error("Device is not paired");
  return client;
}
