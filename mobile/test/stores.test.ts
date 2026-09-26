import type { GatewayEvent, PairDeviceResponse } from "@nanoagent/sdk";
import { describe, expect, test } from "bun:test";

import { getLocale, setLocale } from "../src/i18n";
import { memoryStore } from "../src/lib/storage";
import { STORAGE_KEYS, createAuthStore, isPaired } from "../src/stores/auth";
import { createLabelsStore } from "../src/stores/labels";
import {
  INBOX_KEY,
  INBOX_LIMIT,
  createInboxStore,
  inboxItemFromEvent,
  pushPayloadFromData,
  unreadCount,
} from "../src/stores/notifications";

const PAIRED: PairDeviceResponse = {
  token: "tok_123",
  expires_at: null,
  client: {
    id: "cl_1",
    kind: "device",
    scopes: ["chat", "read", "approve"],
    label: "Phone",
    locale: "en",
    created_at: 1,
    revoked_at: null,
  },
  device: {
    id: "dev_1",
    client_id: "cl_1",
    platform: "ios",
    label: "Phone",
    locale: "en",
    created_at: 1,
    updated_at: 1,
    revoked: false,
  },
};

describe("auth store", () => {
  test("hydrates from storage and honours the device locale", async () => {
    const storage = memoryStore();
    const store = createAuthStore(storage, { deviceLocale: "ar-SA" });
    await store.getState().hydrate();
    expect(store.getState().hydrated).toBe(true);
    expect(store.getState().locale).toBe("ar");
    expect(getLocale()).toBe("ar");
    expect(isPaired(store.getState())).toBe(false);
    setLocale("en");
  });

  test("pair persists token, scopes and device id; unpair keeps the locale", async () => {
    const storage = memoryStore();
    const store = createAuthStore(storage);
    await store.getState().hydrate();
    await store.getState().pair("https://gw:8765", PAIRED);
    expect(isPaired(store.getState())).toBe(true);
    expect(storage.dump()[STORAGE_KEYS.token]).toBe("tok_123");
    expect(JSON.parse(storage.dump()[STORAGE_KEYS.scopes] ?? "[]")).toEqual(["chat", "read", "approve"]);
    expect(store.getState().deviceId).toBe("dev_1");
    expect(store.getState().hasScope("approve")).toBe(true);
    expect(store.getState().hasScope("control")).toBe(false);

    await store.getState().setLocale("ar");
    await store.getState().unpair();
    expect(isPaired(store.getState())).toBe(false);
    expect(store.getState().locale).toBe("ar");
    expect(storage.dump()[STORAGE_KEYS.locale]).toBe("ar");
    expect(storage.dump()[STORAGE_KEYS.token]).toBeUndefined();
    setLocale("en");
  });

  test("admin scope implies every scope; push registration round-trips", async () => {
    const storage = memoryStore();
    const store = createAuthStore(storage);
    await store.getState().hydrate();
    await store.getState().pair("https://gw", { ...PAIRED, client: { ...PAIRED.client, scopes: ["admin"] } });
    expect(store.getState().hasScope("control")).toBe(true);
    await store.getState().setPushRegistration("android", "fcm-token", "dev_9");
    expect(store.getState().pushPlatform).toBe("android");
    expect(store.getState().deviceId).toBe("dev_9");
    await store.getState().clearPushRegistration();
    expect(store.getState().pushToken).toBeUndefined();
  });
});

function event<K extends GatewayEvent["kind"]>(kind: K, data: Extract<GatewayEvent, { kind: K }>["data"], id = "01H"): GatewayEvent {
  return { id, session: "s1", run: "r1", ts: 1_700_000_000_000, kind, data } as GatewayEvent;
}

describe("inbox store", () => {
  test("maps gateway events to inbox items like the push router", () => {
    const approval = inboxItemFromEvent(
      event("approval", { approval_id: "ap_1", type: "execution", summary: "Buy", expires_at: null, actions: ["confirm", "cancel"], status: "pending" }),
    );
    expect(approval).toMatchObject({ kind: "approval", level: "warning", approval_id: "ap_1", deep_link: "nanoagent://approvals/ap_1" });
    expect(
      inboxItemFromEvent(event("approval", { approval_id: "ap_1", type: "execution", summary: "Buy", expires_at: null, status: "confirmed" })),
    ).toBeUndefined();

    const decision = inboxItemFromEvent(
      event("structured", {
        type: "decision",
        result_id: "res_1",
        payload: { verdict: "buy", entry: 1, stop: 1, targets: [], confidence: 0.5, reasons: [], gates_passed: [] },
      }),
    );
    expect(decision).toMatchObject({ kind: "decision", deep_link: "nanoagent://results/res_1", args: { verdict: "buy", result_id: "res_1" } });
    expect(inboxItemFromEvent(event("structured", { type: "market", result_id: "x", payload: {} as never }))).toBeUndefined();

    expect(inboxItemFromEvent(event("job", { job_id: "j1", kind: "goal", status: "failed" }))).toMatchObject({ kind: "job", level: "error", body_key: "push.job.failed" });
    expect(inboxItemFromEvent(event("job", { job_id: "j1", kind: "goal", status: "working" }))).toBeUndefined();
    expect(inboxItemFromEvent(event("delta", { text: "hi" }))).toBeUndefined();
  });

  test("parses FCM data maps with JSON-encoded args", () => {
    const payload = pushPayloadFromData({
      kind: "approval",
      title_key: "push.approval.title",
      body_key: "push.approval.body",
      args: JSON.stringify({ type: "execution" }),
      approval_id: "ap_1",
      deep_link: "nanoagent://approvals/ap_1",
    });
    expect(payload).toEqual({
      kind: "approval",
      title_key: "push.approval.title",
      body_key: "push.approval.body",
      args: { type: "execution" },
      approval_id: "ap_1",
      deep_link: "nanoagent://approvals/ap_1",
    });
    expect(pushPayloadFromData({ foo: "bar" })).toBeUndefined();
    expect(pushPayloadFromData(null)).toBeUndefined();
  });

  test("persists, dedupes, caps and tracks read state", async () => {
    const storage = memoryStore();
    const store = createInboxStore(storage);
    await store.getState().hydrate();
    const item = await store.getState().addPush({ kind: "notification", title_key: "a", body_key: "b" }, { id: "n1", ts: 10 });
    await store.getState().addPush({ kind: "notification", title_key: "a", body_key: "b" }, { id: "n1", ts: 11 });
    expect(store.getState().items).toHaveLength(1);
    expect(unreadCount(store.getState().items)).toBe(1);
    await store.getState().markRead(item.id);
    expect(unreadCount(store.getState().items)).toBe(0);

    for (let index = 0; index < INBOX_LIMIT + 5; index += 1) {
      await store.getState().addPush({ kind: "notification", title_key: "a", body_key: "b" }, { id: `x${index}`, ts: 100 + index });
    }
    expect(store.getState().items).toHaveLength(INBOX_LIMIT);
    expect(store.getState().items[0]?.id).toBe(`x${INBOX_LIMIT + 4}`);

    const reloaded = createInboxStore(storage);
    await reloaded.getState().hydrate();
    expect(reloaded.getState().items).toHaveLength(INBOX_LIMIT);
    await reloaded.getState().clear();
    expect(storage.dump()[INBOX_KEY]).toBeUndefined();
  });
});

describe("labels store", () => {
  test("resolves server catalog, then bundled, then key", async () => {
    const store = createLabelsStore();
    const client = { getLabels: async () => ({ locale: "en", dir: "ltr", supported: ["en"], labels: { "tabs.agent": "Bot", "gw.only": "Gateway" } }) };
    await store.getState().load(client as never, "en");
    expect(store.getState().resolve("tabs.agent", "en")).toBe("Bot");
    expect(store.getState().resolve("gw.only", "en")).toBe("Gateway");
    expect(store.getState().resolve("tabs.tasks", "en")).toBe("Tasks");
    expect(store.getState().resolve("missing.key", "ar")).toBe("missing.key");
  });

  test("load errors are recorded, not thrown", async () => {
    const store = createLabelsStore();
    const client = { getLabels: async () => Promise.reject(new Error("offline")) };
    await store.getState().load(client as never, "ar");
    expect(store.getState().error).toBeInstanceOf(Error);
    expect(store.getState().loading).toBe(false);
  });
});
