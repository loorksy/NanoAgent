import { describe, expect, test } from "bun:test";

import { isPairingCode, normalizeGatewayUrl, parseDeepLink, routeFor } from "../src/lib/deeplink";

describe("normalizeGatewayUrl", () => {
  test("adds https, strips trailing slash and pairing path", () => {
    expect(normalizeGatewayUrl("bot.example.com:8765")).toBe("https://bot.example.com:8765");
    expect(normalizeGatewayUrl("http://10.0.0.5:8765/")).toBe("http://10.0.0.5:8765");
    expect(normalizeGatewayUrl("https://bot.example.com/api/v2/devices/pair?code=1")).toBe("https://bot.example.com");
    expect(normalizeGatewayUrl("https://bot.example.com/prefix/api/v2")).toBe("https://bot.example.com/prefix");
  });

  test("rejects non-http schemes and garbage", () => {
    expect(normalizeGatewayUrl("ftp://x")).toBeUndefined();
    expect(normalizeGatewayUrl("")).toBeUndefined();
    expect(normalizeGatewayUrl("http://")).toBeUndefined();
  });
});

describe("parseDeepLink", () => {
  test("pairing via custom scheme, https pair_url and QR JSON", () => {
    expect(parseDeepLink("nanoagent://pair?url=https%3A%2F%2Fgw.local%3A8765&code=12345678&label=Phone")).toEqual({
      kind: "pair",
      url: "https://gw.local:8765",
      code: "12345678",
      label: "Phone",
    });
    expect(parseDeepLink("https://gw.local:8765/api/v2/devices/pair?code=12345678")).toEqual({
      kind: "pair",
      url: "https://gw.local:8765",
      code: "12345678",
    });
    expect(parseDeepLink(JSON.stringify({ gateway: "gw.local", code: "123456" }))).toEqual({
      kind: "pair",
      url: "https://gw.local",
      code: "123456",
    });
    expect(parseDeepLink(JSON.stringify({ url: "gw.local", code: "abc" }))).toBeUndefined();
  });

  test("push deep links", () => {
    expect(parseDeepLink("nanoagent://approvals/ap_1")).toEqual({ kind: "approval", id: "ap_1" });
    expect(parseDeepLink("nanoagent://approvals/ap_1?session=s1")).toEqual({ kind: "approval", id: "ap_1", session: "s1" });
    expect(parseDeepLink("nanoagent://sessions/s1")).toEqual({ kind: "session", id: "s1" });
    expect(parseDeepLink("nanoagent://sessions")).toEqual({ kind: "tab", name: "agent" });
    expect(parseDeepLink("nanoagent://results/r1")).toEqual({ kind: "result", id: "r1" });
    expect(parseDeepLink("nanoagent://jobs/j1")).toEqual({ kind: "job", id: "j1" });
    expect(parseDeepLink("nanoagent://connect")).toEqual({ kind: "tab", name: "connect" });
    expect(parseDeepLink("nanoagent://nope/x")).toBeUndefined();
    expect(parseDeepLink("not a url")).toBeUndefined();
  });

  test("isPairingCode accepts 6-10 digits only", () => {
    expect(isPairingCode(" 123456 ")).toBe(true);
    expect(isPairingCode("12345")).toBe(false);
    expect(isPairingCode("12345678901")).toBe(false);
    expect(isPairingCode("12a456")).toBe(false);
  });
});

describe("routeFor", () => {
  test("maps every link kind to an expo-router path", () => {
    expect(routeFor({ kind: "pair", url: "https://gw", code: "123456" })).toBe("/pairing?url=https%3A%2F%2Fgw&code=123456");
    expect(routeFor({ kind: "approval", id: "a/1" })).toBe("/tasks?approval=a%2F1");
    expect(routeFor({ kind: "session", id: "s1" })).toBe("/?session=s1");
    expect(routeFor({ kind: "result", id: "r1" })).toBe("/result/r1");
    expect(routeFor({ kind: "job", id: "j1" })).toBe("/tasks?job=j1");
    expect(routeFor({ kind: "tab", name: "agent" })).toBe("/");
    expect(routeFor({ kind: "tab", name: "log" })).toBe("/log");
  });
});
