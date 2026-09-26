import type { GatewayClient, Labels } from "@nanoagent/sdk";
import { createStore } from "zustand/vanilla";

import { label as localLabel, type Locale, type Params } from "../i18n";

export interface LabelsState {
  catalogs: Partial<Record<Locale, Labels>>;
  loading: boolean;
  error: unknown;
}

export interface LabelsActions {
  load(client: GatewayClient, locale: Locale, options?: { force?: boolean }): Promise<void>;
  /** Server catalog first, then the bundled catalog, then the raw key. */
  resolve(key: string, locale: Locale, params?: Params): string;
}

export type LabelsStore = LabelsState & LabelsActions;

export function createLabelsStore() {
  return createStore<LabelsStore>()((set, get) => ({
    catalogs: {},
    loading: false,
    error: undefined,

    async load(client, locale, options = {}) {
      if (!options.force && get().catalogs[locale]) return;
      set({ loading: true });
      try {
        const response = await client.getLabels(locale);
        set((state) => ({
          catalogs: { ...state.catalogs, [locale]: response.labels },
          loading: false,
          error: undefined,
        }));
      } catch (error) {
        set({ loading: false, error });
      }
    },

    resolve(key, locale, params) {
      return localLabel(key, get().catalogs[locale] ?? null, params);
    },
  }));
}

export type LabelsStoreApi = ReturnType<typeof createLabelsStore>;
