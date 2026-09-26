import { describe, expect, test } from "bun:test";

import { GatewayClient, GatewayError } from "../src/client.ts";

interface Recorded {
  url: string;
  method: string | undefined;
  headers: Record<string, string>;
  body: unknown;
}

function fakeFetch(responder: (call: Recorded) => Response | Promise<Response>) {
  const calls: Recorded[] = [];
  const fetchImpl = async (url: string, init?: RequestInit): Promise<Response> => {
    const headers: Record<string, string> = {};
    for (const [key, value] of Object.entries((init?.headers ?? {}) as Record<string, string>)) {
      headers[key] = value;
    }
    const call: Recorded = {
      url,
      method: init?.method,
      headers,
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    };
    calls.push(call);
    return responder(call);
  };
  return { calls, fetchImpl };
}

const json = (value: unknown, status = 200): Response =>
  new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

describe("GatewayClient", () => {
  test("builds URLs under /api/v2 and sends bearer + session headers", async () => {
    const { calls, fetchImpl } = fakeFetch(() => json({ sessions: [] }));
    const client = new GatewayClient({
      baseUrl: "https://gw.example.com:8765/",
      token: "abc",
      session: "chat-42",
      locale: "ar",
      fetch: fetchImpl,
    });
    await client.listSessions();
    expect(calls[0]?.url).toBe("https://gw.example.com:8765/api/v2/sessions");
    expect(calls[0]?.method).toBe("GET");
    expect(calls[0]?.headers).toMatchObject({
      Authorization: "Bearer abc",
      "X-Mokli-Session": "chat-42",
      "Accept-Language": "ar",
      Accept: "application/json",
    });
    expect(calls[0]?.headers["Content-Type"]).toBeUndefined();
  });

  test("token can be async and omitted when absent", async () => {
    const { calls, fetchImpl } = fakeFetch(() => json({}));
    const client = new GatewayClient({ baseUrl: "http://h", token: async () => undefined, fetch: fetchImpl });
    await client.me();
    expect(calls[0]?.headers["Authorization"]).toBeUndefined();
    client.setToken(async () => "later");
    await client.me();
    expect(calls[1]?.headers["Authorization"]).toBe("Bearer later");
  });

  test("session routes: messages, cancel, state, timeline, events url", async () => {
    const { calls, fetchImpl } = fakeFetch(() => json({ run_id: "r_9" }));
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    const sent = await client.sendMessage("s/1", { text: "hi" });
    expect(sent.run_id).toBe("r_9");
    expect(calls[0]).toMatchObject({
      url: "http://h/api/v2/sessions/s%2F1/messages",
      method: "POST",
      body: { text: "hi" },
    });
    expect(calls[0]?.headers["Content-Type"]).toBe("application/json");
    await client.cancel("s1");
    expect(calls[1]).toMatchObject({ url: "http://h/api/v2/sessions/s1/cancel", method: "POST" });
    await client.getState("s1");
    expect(calls[2]?.url).toBe("http://h/api/v2/sessions/s1/state");
    await client.getTimeline("s1", "01X");
    expect(calls[3]?.url).toBe("http://h/api/v2/sessions/s1/timeline?after=01X");
    await client.getTimeline("s1");
    expect(calls[4]?.url).toBe("http://h/api/v2/sessions/s1/timeline");
    expect(client.eventsUrl("s1", "01X")).toBe("http://h/api/v2/sessions/s1/events?after=01X");
    expect(client.wsUrl()).toBe("ws://h/ws/v2");
    expect(new GatewayClient({ baseUrl: "https://h", fetch: fetchImpl }).wsUrl()).toBe("wss://h/ws/v2");
  });

  test("list endpoints unwrap the gateway envelopes", async () => {
    const { fetchImpl } = fakeFetch((call) => {
      if (call.url.endsWith("/sessions")) return json({ sessions: [{ id: "s1", title: "", created_at: 1, state: "working" }] });
      if (call.url.includes("/approvals?")) {
        return json({ approvals: [{ id: "a1", type: "execution", status: "pending", summary: "buy", expires_at: null }] });
      }
      if (call.url.endsWith("/jobs")) return json({ jobs: [{ job_id: "j1", kind: "cron", status: "scheduled" }] });
      if (call.url.includes("/recommendations/live")) return json({ live: null, session: "s1" });
      if (call.url.includes("/recommendations")) return json({ recommendations: [{ id: "r1" }], count: 1 });
      if (call.url.includes("/labels")) return json({ locale: "ar", dir: "rtl", supported: ["ar", "en"], labels: { a: "أ" } });
      if (call.url.includes("/devices")) return json({ devices: [{ id: "d1" }] });
      return json({});
    });
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    expect((await client.listSessions())[0]?.state).toBe("working");
    const approvals = await client.listApprovals();
    expect(approvals[0]).toMatchObject({ id: "a1", approval_id: "a1", status: "pending" });
    expect((await client.listJobs())[0]?.job_id).toBe("j1");
    expect(await client.getLiveRecommendation("s1")).toBeNull();
    expect((await client.listRecommendations({ session: "s1" }))[0]?.id).toBe("r1");
    const labels = await client.getLabels("ar");
    expect(labels.dir).toBe("rtl");
    expect(labels.labels["a"]).toBe("أ");
    expect((await client.listDevices())[0]?.id).toBe("d1");
  });

  test("approvals, jobs, connect and devices routes", async () => {
    const { calls, fetchImpl } = fakeFetch(() => json({ id: "a1", approvals: [], jobs: [], devices: [] }));
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    await client.listApprovals();
    await client.listApprovals("confirmed");
    await client.decideApproval("a1", "confirm");
    await client.pauseJob("j1");
    await client.resumeJob("j1");
    await client.cancelJob("j1");
    await client.deleteJob("j1");
    await client.kill();
    await client.kill(false);
    await client.pause(true);
    await client.pause(false);
    await client.setPaperMode(false);
    await client.setRiskProfile("aggressive");
    await client.setRiskField("min_rr", 2.5);
    await client.updateRisk({ values: { min_rr: 2 }, toggles: { news_shield: true } });
    await client.setMt5Permissions({ level: "execute", max_lot_per_order: 0.1 });
    await client.getMt5Permissions();
    await client.getLabels("ar");
    await client.getLog({ kinds: ["decision", "gate"], from: 10 });
    await client.registerDevice({ platform: "android", push_token: "fcm" });
    await client.pairDevice({ code: "1234", platform: "ios", label: "iPhone", push_token: "apns" });
    await client.createPairingCode({ label: "phone" });
    await client.deleteDevice("d1");
    const summary = calls.map((call) => `${call.method} ${call.url.replace("http://h/api/v2", "")}`);
    expect(summary).toEqual([
      "GET /approvals?status=pending",
      "GET /approvals?status=confirmed",
      "POST /approvals/a1",
      "POST /jobs/j1/pause",
      "POST /jobs/j1/resume",
      "POST /jobs/j1/cancel",
      "DELETE /jobs/j1",
      "POST /control/kill",
      "POST /control/kill",
      "POST /control/pause",
      "POST /control/resume",
      "POST /control/paper-mode",
      "PUT /connect/risk-profile",
      "PUT /connect/risk/min_rr",
      "PUT /connect/risk",
      "PUT /connect/mt5/permissions",
      "GET /connect/mt5/permissions",
      "GET /labels?locale=ar",
      "GET /log?kinds=decision%2Cgate&from=10",
      "POST /devices",
      "POST /devices/pair",
      "POST /devices/pairing-codes",
      "DELETE /devices/d1",
    ]);
    expect(calls[2]?.body).toEqual({ decision: "confirm" });
    expect(calls[7]?.body).toEqual({ enabled: true });
    expect(calls[8]?.body).toEqual({ enabled: false });
    expect(calls[9]?.body).toEqual({ enabled: true });
    expect(calls[10]?.body).toBeUndefined();
    expect(calls[11]?.body).toEqual({ enabled: false });
    expect(calls[12]?.body).toEqual({ name: "aggressive" });
    expect(calls[13]?.body).toEqual({ value: 2.5, derive: true });
    expect(calls[15]?.body).toEqual({ permissions: { level: "execute", max_lot_per_order: 0.1 } });
    expect(calls[20]?.body).toEqual({ code: "1234", platform: "ios", label: "iPhone", push_token: "apns" });
  });

  test("results html uses text/html accept and returns text", async () => {
    const { calls, fetchImpl } = fakeFetch(() => new Response("<div>ok</div>", { status: 200 }));
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    const html = await client.getResultHtml("res1", "ar");
    expect(html).toBe("<div>ok</div>");
    expect(calls[0]?.url).toBe("http://h/api/v2/results/res1/html?locale=ar");
    expect(calls[0]?.headers["Accept"]).toBe("text/html");
  });

  test("errors surface code and message_key from the gateway envelope", async () => {
    const { fetchImpl } = fakeFetch(() =>
      json({ error: { code: "scope_missing", message_key: "error.scope.approve", details: { need: "approve" } } }, 403),
    );
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    const error = await client.decideApproval("a1", "confirm").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(GatewayError);
    const typed = error as GatewayError;
    expect(typed.status).toBe(403);
    expect(typed.code).toBe("scope_missing");
    expect(typed.messageKey).toBe("error.scope.approve");
    expect(typed.details).toEqual({ need: "approve" });
  });

  test("non-JSON error bodies fall back to http code", async () => {
    const { fetchImpl } = fakeFetch(() => new Response("gateway down", { status: 502 }));
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    const error = (await client.getJob("j1").catch((e: unknown) => e)) as GatewayError;
    expect(error.code).toBe("http_502");
    expect(error.messageKey).toBe("error.http");
  });

  test("204 responses resolve to undefined", async () => {
    const { fetchImpl } = fakeFetch(() => new Response(null, { status: 204 }));
    const client = new GatewayClient({ baseUrl: "http://h", fetch: fetchImpl });
    await expect(client.deleteSession("s1")).resolves.toBeUndefined();
  });
});
