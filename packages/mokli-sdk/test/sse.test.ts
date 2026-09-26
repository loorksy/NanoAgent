import { describe, expect, test } from "bun:test";

import { GatewayClient } from "../src/client.ts";
import { SseParser, parseGatewayEvent, subscribe } from "../src/sse.ts";
import type { GatewayEvent } from "../src/types.ts";

function event(id: string, kind: GatewayEvent["kind"], data: unknown): string {
  return JSON.stringify({ id, session: "s_1", run: "r_1", ts: 1, kind, data });
}

describe("SseParser", () => {
  test("parses a simple message with id and data", () => {
    const parser = new SseParser();
    const messages = parser.feed('id: 1\ndata: {"a":1}\n\n');
    expect(messages).toEqual([{ id: "1", data: '{"a":1}' }]);
    expect(parser.lastEventId).toBe("1");
  });

  test("handles chunks split mid-line and mid-event", () => {
    const parser = new SseParser();
    expect(parser.feed("id: 0")).toEqual([]);
    expect(parser.feed("1\nda")).toEqual([]);
    expect(parser.feed("ta: hello\n")).toEqual([]);
    expect(parser.feed("\n")).toEqual([{ id: "01", data: "hello" }]);
  });

  test("joins multi-line data with newlines", () => {
    const parser = new SseParser();
    const messages = parser.feed("data: line1\ndata: line2\ndata:\n\n");
    expect(messages).toEqual([{ data: "line1\nline2\n" }]);
  });

  test("supports CRLF and lone CR line endings", () => {
    const parser = new SseParser();
    expect(parser.feed("data: a\r\n\r\n")).toEqual([{ data: "a" }]);
    // A trailing CR must wait for the next chunk: it may be the first half of a CRLF.
    expect(parser.feed("data: b\r\r")).toEqual([]);
    expect(parser.feed("data: c\r")).toEqual([{ data: "b" }]);
    expect(parser.feed("\nid: 9\r\n\r\n")).toEqual([{ id: "9", data: "c" }]);
  });

  test("ignores comments and unknown fields, strips one leading space", () => {
    const parser = new SseParser();
    const messages = parser.feed(": keep-alive\nfoo: bar\ndata:  two spaces\n\n");
    expect(messages).toEqual([{ data: " two spaces" }]);
  });

  test("event without data is not dispatched but id persists", () => {
    const parser = new SseParser();
    expect(parser.feed("id: 42\n\n")).toEqual([]);
    expect(parser.lastEventId).toBe("42");
    expect(parser.feed("data: x\n\n")).toEqual([{ id: "42", data: "x" }]);
  });

  test("id containing NUL is ignored", () => {
    const parser = new SseParser();
    parser.feed("id: bad\u0000id\ndata: x\n\n");
    expect(parser.lastEventId).toBeUndefined();
  });

  test("retry field is parsed and non-numeric retry ignored", () => {
    const parser = new SseParser();
    expect(parser.feed("retry: 2500\ndata: x\n\n")).toEqual([{ data: "x", retry: 2500 }]);
    expect(parser.feed("retry: soon\ndata: y\n\n")).toEqual([{ data: "y" }]);
  });

  test("event type is carried through", () => {
    const parser = new SseParser();
    expect(parser.feed("event: heartbeat\ndata: {}\n\n")).toEqual([{ event: "heartbeat", data: "{}" }]);
  });
});

describe("parseGatewayEvent", () => {
  test("accepts well-formed events and rejects malformed ones", () => {
    expect(parseGatewayEvent(event("1", "delta", { text: "hi" }))?.kind).toBe("delta");
    expect(parseGatewayEvent("not json")).toBeUndefined();
    expect(parseGatewayEvent('{"id":"1"}')).toBeUndefined();
    expect(parseGatewayEvent('{"kind":"delta","id":"1","data":"x"}')).toBeUndefined();
  });
});

interface Call {
  url: string;
  headers: Record<string, string>;
}

function streamResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
}

function headersToRecord(init: RequestInit | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  const headers = init?.headers;
  if (!headers) return out;
  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      out[key.toLowerCase()] = value;
    });
    return out;
  }
  if (Array.isArray(headers)) {
    for (const [key, value] of headers) out[key.toLowerCase()] = value;
    return out;
  }
  for (const [key, value] of Object.entries(headers)) out[key.toLowerCase()] = value;
  return out;
}

describe("subscribe", () => {
  test("streams events, reconnects after drop and resumes with Last-Event-ID", async () => {
    const calls: Call[] = [];
    const responses = [
      streamResponse([
        `id: 01A\ndata: ${event("01A", "state", { state: "working" })}\n\n`,
        `id: 01B\ndata: ${event("01B", "delta", { text: "hel" })}\n\n`,
      ]),
      streamResponse([], 503),
      streamResponse([
        `id: 01C\ndata: ${event("01C", "delta", { text: "lo" })}\n\n`,
        `id: 01D\ndata: ${event("01D", "end", { run: "r_1", outcome: "ok" })}\n\n`,
      ]),
    ];
    const client = new GatewayClient({
      baseUrl: "https://gw.test",
      token: "tok",
      fetch: async (url, init) => {
        calls.push({ url, headers: headersToRecord(init) });
        return responses.shift() ?? streamResponse([]);
      },
    });
    const controller = new AbortController();
    const sleeps: number[] = [];
    const seen: string[] = [];
    const statuses: string[] = [];
    for await (const item of subscribe(client, "s_1", {
      after: "000",
      signal: controller.signal,
      backoff: { initialMs: 100, factor: 2, maxMs: 1000 },
      sleep: async (ms) => {
        sleeps.push(ms);
      },
      onStatus: (status) => statuses.push(status),
    })) {
      seen.push(item.id);
      if (item.kind === "end") controller.abort();
    }
    expect(seen).toEqual(["01A", "01B", "01C", "01D"]);
    expect(calls[0]?.url).toBe("https://gw.test/api/v2/sessions/s_1/events?after=000");
    expect(calls[0]?.headers["last-event-id"]).toBe("000");
    expect(calls[0]?.headers["authorization"]).toBe("Bearer tok");
    expect(calls[0]?.headers["accept"]).toBe("text/event-stream");
    expect(calls[1]?.headers["last-event-id"]).toBe("01B");
    expect(calls[2]?.url).toBe("https://gw.test/api/v2/sessions/s_1/events?after=01B");
    expect(sleeps.length).toBe(2);
    expect(sleeps[1]).toBe(200);
    expect(statuses[0]).toBe("connecting");
    expect(statuses).toContain("reconnecting");
    expect(statuses[statuses.length - 1]).toBe("closed");
  });

  test("honours server retry hint and stops after maxRetries", async () => {
    let calls = 0;
    const client = new GatewayClient({
      baseUrl: "https://gw.test/",
      fetch: async () => {
        calls += 1;
        return calls === 1 ? streamResponse(["retry: 50\n\n"]) : streamResponse([], 500);
      },
    });
    const sleeps: number[] = [];
    const seen: GatewayEvent[] = [];
    for await (const item of subscribe(client, "s_2", {
      maxRetries: 2,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    })) {
      seen.push(item);
    }
    expect(seen).toEqual([]);
    expect(sleeps[0]).toBe(50);
    // one clean stream + initial attempt + 2 retries
    expect(calls).toBe(4);
  });

  test("throws on 401 instead of retrying", async () => {
    const client = new GatewayClient({
      baseUrl: "https://gw.test",
      fetch: async () => new Response(JSON.stringify({ error: { code: "unauthorized", message_key: "error.auth" } }), { status: 401 }),
    });
    const iterator = subscribe(client, "s_3", { sleep: async () => {} });
    await expect(iterator.next()).rejects.toMatchObject({ status: 401 });
  });

  test("falls back to non-streaming bodies", async () => {
    const client = new GatewayClient({
      baseUrl: "https://gw.test",
      fetch: async () => {
        const response = new Response(`data: ${event("1", "delta", { text: "x" })}\n\n`);
        Object.defineProperty(response, "body", { value: null });
        return response;
      },
    });
    const controller = new AbortController();
    const ids: string[] = [];
    for await (const item of subscribe(client, "s_4", { signal: controller.signal, sleep: async () => {} })) {
      ids.push(item.id);
      controller.abort();
    }
    expect(ids).toEqual(["1"]);
  });
});
