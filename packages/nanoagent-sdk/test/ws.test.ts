import { describe, expect, test } from "bun:test";

import { GatewayClient } from "../src/client.ts";
import { GatewayWebSocket, parseServerMessage, type WebSocketLike } from "../src/ws.ts";
import type { GatewayEvent } from "../src/types.ts";

class FakeSocket implements WebSocketLike {
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: ((event: unknown) => void) | null = null;
  onclose: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;

  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }

  open(): void {
    this.readyState = 1;
    this.onopen?.({});
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = 3;
    this.onclose?.({});
  }

  emit(message: unknown): void {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

const tick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

describe("GatewayWebSocket", () => {
  test("passes token in query, queues messages until open, resubscribes with last id", async () => {
    FakeSocket.instances = [];
    const client = new GatewayClient({ baseUrl: "https://gw.test", token: "tok", fetch: async () => new Response() });
    const events: GatewayEvent[] = [];
    const statuses: string[] = [];
    const ws = new GatewayWebSocket(client, {
      factory: (url) => new FakeSocket(url),
      sleep: async () => {},
      pingIntervalMs: 0,
      onStatus: (status) => statuses.push(status),
    });
    ws.onEvent((event) => events.push(event));
    ws.subscribe("s_1");
    ws.sendMessage("s_1", "hello", undefined, "req1");
    await ws.connect();
    await tick();
    const first = FakeSocket.instances[0]!;
    expect(first.url).toBe("wss://gw.test/ws/v2?token=tok");
    expect(first.sent).toEqual([]);
    first.open();
    expect(first.sent.map((s) => JSON.parse(s))).toEqual([
      { type: "subscribe", session: "s_1" },
      { type: "send", session: "s_1", text: "hello", request_id: "req1" },
    ]);
    first.emit({
      type: "event",
      event: { id: "01Z", session: "s_1", ts: 1, kind: "delta", data: { text: "x" } },
    });
    expect(events).toHaveLength(1);
    ws.approve("a1", "confirm", "s_1");
    expect(JSON.parse(first.sent[2]!)).toEqual({ type: "approve", approval_id: "a1", decision: "confirm", session: "s_1" });

    first.close();
    await tick();
    await tick();
    const second = FakeSocket.instances[1]!;
    second.open();
    expect(JSON.parse(second.sent[0]!)).toEqual({ type: "subscribe", session: "s_1", after: "01Z" });
    expect(statuses).toEqual(["connecting", "open", "reconnecting", "open"]);
    ws.close();
    expect(statuses[statuses.length - 1]).toBe("closed");
  });

  test("parseServerMessage rejects garbage", () => {
    expect(parseServerMessage("nope")).toBeUndefined();
    expect(parseServerMessage(42)).toBeUndefined();
    expect(parseServerMessage('{"type":"pong"}')).toEqual({ type: "pong" });
  });
});
