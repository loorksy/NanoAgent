import type { GatewayEvent, NotificationLevel, PushPayload } from "@nanoagent/sdk";
import { createStore } from "zustand/vanilla";

import type { KeyValueStore } from "../lib/storage";

export const INBOX_KEY = "nanoagent.inbox";
export const INBOX_LIMIT = 100;

export type InboxSource = "push" | "event";

export interface InboxItem {
  id: string;
  ts: number;
  source: InboxSource;
  kind: PushPayload["kind"];
  level: NotificationLevel;
  title_key: string;
  body_key: string;
  args: Record<string, string | number | boolean | null>;
  session?: string;
  deep_link?: string;
  approval_id?: string;
  read: boolean;
}

export interface InboxState {
  items: InboxItem[];
  hydrated: boolean;
}

export interface InboxActions {
  hydrate(): Promise<void>;
  addPush(payload: PushPayload, options?: { id?: string; ts?: number }): Promise<InboxItem>;
  addEvent(event: GatewayEvent): Promise<InboxItem | undefined>;
  markRead(id: string): Promise<void>;
  markAllRead(): Promise<void>;
  clear(): Promise<void>;
}

export type InboxStore = InboxState & InboxActions;

function levelFor(kind: PushPayload["kind"], args: Record<string, unknown>): NotificationLevel {
  const level = args["level"];
  if (level === "warning" || level === "error" || level === "info") return level;
  if (kind === "approval") return "warning";
  return "info";
}

function stringArgs(input: Record<string, unknown> | undefined): Record<string, string | number | boolean | null> {
  const out: Record<string, string | number | boolean | null> = {};
  for (const [key, value] of Object.entries(input ?? {})) {
    if (value === null || ["string", "number", "boolean"].includes(typeof value)) {
      out[key] = value as string | number | boolean | null;
    }
  }
  return out;
}

/** Mirrors `payload_for` in `nanobot/agent_api/push/router.py` for events seen while connected. */
export function inboxItemFromEvent(event: GatewayEvent): InboxItem | undefined {
  const base = { id: event.id, ts: event.ts, source: "event" as const, session: event.session, read: false };
  switch (event.kind) {
    case "approval": {
      if (event.data.status && event.data.status !== "pending") return undefined;
      return {
        ...base,
        kind: "approval",
        level: "warning",
        title_key: "push.approval.title",
        body_key: "push.approval.body",
        args: { type: event.data.type },
        deep_link: `nanoagent://approvals/${event.data.approval_id}`,
        approval_id: event.data.approval_id,
      };
    }
    case "notification":
      return {
        ...base,
        kind: "notification",
        level: event.data.level,
        title_key: event.data.title,
        body_key: event.data.body,
        args: stringArgs(event.data.args),
        deep_link: event.data.deep_link ?? `nanoagent://sessions/${event.session}`,
      };
    case "structured":
      if (event.data.type !== "decision") return undefined;
      return {
        ...base,
        kind: "decision",
        level: "info",
        title_key: "push.decision.title",
        body_key: "push.decision.body",
        args: { verdict: event.data.payload.verdict, result_id: event.data.result_id },
        deep_link: `nanoagent://results/${event.data.result_id}`,
      };
    case "job":
      if (!["finished", "failed", "error"].includes(event.data.status)) return undefined;
      return {
        ...base,
        kind: "job",
        level: event.data.status === "finished" ? "info" : "error",
        title_key: "push.job.title",
        body_key: `push.job.${event.data.status}`,
        args: { job_id: event.data.job_id, kind: event.data.kind },
        deep_link: `nanoagent://jobs/${event.data.job_id}`,
      };
    default:
      return undefined;
  }
}

export function inboxItemFromPush(payload: PushPayload, options: { id?: string; ts?: number } = {}): InboxItem {
  const args = stringArgs(payload.args);
  const item: InboxItem = {
    id: options.id ?? `push-${options.ts ?? Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    ts: options.ts ?? Date.now(),
    source: "push",
    kind: payload.kind,
    level: levelFor(payload.kind, args),
    title_key: payload.title_key,
    body_key: payload.body_key,
    args,
    read: false,
  };
  if (payload.session) item.session = payload.session;
  if (payload.deep_link) item.deep_link = payload.deep_link;
  if (payload.approval_id) item.approval_id = payload.approval_id;
  return item;
}

/** Parse the `data` map of an FCM/APNs message (values may be JSON-encoded strings). */
export function pushPayloadFromData(data: Record<string, unknown> | null | undefined): PushPayload | undefined {
  if (!data || typeof data["kind"] !== "string" || typeof data["title_key"] !== "string") return undefined;
  const decode = (value: unknown): unknown => {
    if (typeof value !== "string") return value;
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  };
  const args = decode(data["args"]);
  const payload: PushPayload = {
    kind: data["kind"] as PushPayload["kind"],
    title_key: data["title_key"],
    body_key: typeof data["body_key"] === "string" ? data["body_key"] : "push.notification.body",
  };
  if (args && typeof args === "object") payload.args = stringArgs(args as Record<string, unknown>) as Record<string, string | number>;
  if (typeof data["session"] === "string") payload.session = data["session"];
  if (typeof data["deep_link"] === "string") payload.deep_link = data["deep_link"];
  if (typeof data["approval_id"] === "string") payload.approval_id = data["approval_id"];
  return payload;
}

function insert(items: InboxItem[], item: InboxItem): InboxItem[] {
  const without = items.filter((existing) => existing.id !== item.id);
  return [item, ...without].sort((a, b) => b.ts - a.ts).slice(0, INBOX_LIMIT);
}

export function createInboxStore(storage: KeyValueStore) {
  const persist = async (items: InboxItem[]) => storage.set(INBOX_KEY, JSON.stringify(items));
  return createStore<InboxStore>()((set, get) => ({
    items: [],
    hydrated: false,

    async hydrate() {
      const raw = await storage.get(INBOX_KEY);
      let items: InboxItem[] = [];
      if (raw) {
        try {
          const parsed: unknown = JSON.parse(raw);
          if (Array.isArray(parsed)) items = parsed as InboxItem[];
        } catch {
          items = [];
        }
      }
      set({ items, hydrated: true });
    },

    async addPush(payload, options) {
      const item = inboxItemFromPush(payload, options);
      const items = insert(get().items, item);
      set({ items });
      await persist(items);
      return item;
    },

    async addEvent(event) {
      const item = inboxItemFromEvent(event);
      if (!item) return undefined;
      const items = insert(get().items, item);
      set({ items });
      await persist(items);
      return item;
    },

    async markRead(id) {
      const items = get().items.map((item) => (item.id === id ? { ...item, read: true } : item));
      set({ items });
      await persist(items);
    },

    async markAllRead() {
      const items = get().items.map((item) => (item.read ? item : { ...item, read: true }));
      set({ items });
      await persist(items);
    },

    async clear() {
      set({ items: [] });
      await storage.remove(INBOX_KEY);
    },
  }));
}

export type InboxStoreApi = ReturnType<typeof createInboxStore>;

export function unreadCount(items: InboxItem[]): number {
  return items.reduce((count, item) => (item.read ? count : count + 1), 0);
}
