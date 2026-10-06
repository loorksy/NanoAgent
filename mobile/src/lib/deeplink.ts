/**
 * Deep links understood by the app.
 *
 * Pairing (QR or link):
 *   mokli://pair?url=<gateway>&code=<8 digits>
 *   https://<gateway>/api/v2/devices/pair?code=<8 digits>
 *   {"url": "<gateway>", "code": "<8 digits>"}   (also `gateway` / `pair_url`)
 *
 * Push payload `deep_link` values (mokli/agent_api/push/router.py):
 *   mokli://approvals/<id>  mokli://sessions/<id>
 *   mokli://results/<id>    mokli://jobs/<id>
 */

export const APP_SCHEME = "mokli";
export const PAIR_PATH = "/api/v2/devices/pair";

export type DeepLink =
  | { kind: "pair"; url: string; code: string; label?: string }
  | { kind: "approval"; id: string; session?: string }
  | { kind: "session"; id: string }
  | { kind: "result"; id: string; session?: string }
  | { kind: "job"; id: string }
  | { kind: "tab"; name: "agent" | "tasks" | "recommendations" | "connect" | "log" };

const CODE_RE = /^\d{6,10}$/;

export function isPairingCode(value: string): boolean {
  return CODE_RE.test(value.trim());
}

/** Accepts `host`, `host:8766`, `https://host/...` and returns a normalised origin. */
export function normalizeGatewayUrl(raw: string): string | undefined {
  let value = raw.trim();
  if (!value) return undefined;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) value = `https://${value}`;
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return undefined;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return undefined;
  if (!parsed.hostname) return undefined;
  // Drop the pairing path when the operator pasted the `pair_url` returned by the gateway.
  let path = parsed.pathname.replace(/\/+$/, "");
  if (path.endsWith(PAIR_PATH)) path = path.slice(0, -PAIR_PATH.length);
  if (path.endsWith("/api/v2")) path = path.slice(0, -"/api/v2".length);
  return `${parsed.protocol}//${parsed.host}${path}`;
}

function pairFrom(url: string | null | undefined, code: string | null | undefined, label?: string | null): DeepLink | undefined {
  if (!url || !code) return undefined;
  const gateway = normalizeGatewayUrl(url);
  if (!gateway || !isPairingCode(code)) return undefined;
  const link: DeepLink = { kind: "pair", url: gateway, code: code.trim() };
  if (label) link.label = label;
  return link;
}

function fromJson(raw: string): DeepLink | undefined {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return undefined;
  }
  if (!parsed || typeof parsed !== "object") return undefined;
  const record = parsed as Record<string, unknown>;
  const url = [record["url"], record["gateway"], record["gateway_url"], record["pair_url"]].find(
    (candidate): candidate is string => typeof candidate === "string",
  );
  const code = typeof record["code"] === "string" ? record["code"] : undefined;
  const label = typeof record["label"] === "string" ? record["label"] : undefined;
  return pairFrom(url, code, label);
}

export function parseDeepLink(raw: string): DeepLink | undefined {
  const value = raw.trim();
  if (!value) return undefined;
  if (value.startsWith("{")) return fromJson(value);

  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return undefined;
  }

  if (parsed.protocol === `${APP_SCHEME}:`) {
    // `mokli://pair?...` parses with host "pair"; `mokli:///pair` with pathname "/pair".
    const segments = [parsed.host, ...parsed.pathname.split("/")].filter(Boolean);
    const [head, id] = segments;
    const params = parsed.searchParams;
    switch (head) {
      case "pair":
        return pairFrom(params.get("url") ?? params.get("gateway"), params.get("code"), params.get("label"));
      case "approvals":
      case "approval":
        if (!id) return undefined;
        return params.get("session")
          ? { kind: "approval", id, session: params.get("session") ?? undefined }
          : { kind: "approval", id };
      case "sessions":
      case "session":
        return id ? { kind: "session", id } : { kind: "tab", name: "agent" };
      case "results":
      case "result":
        if (!id) return undefined;
        return params.get("session")
          ? { kind: "result", id, session: params.get("session") ?? undefined }
          : { kind: "result", id };
      case "jobs":
      case "job":
        return id ? { kind: "job", id } : { kind: "tab", name: "tasks" };
      case "agent":
      case "tasks":
      case "recommendations":
      case "connect":
      case "log":
        return { kind: "tab", name: head };
      default:
        return undefined;
    }
  }

  if ((parsed.protocol === "https:" || parsed.protocol === "http:") && parsed.pathname.endsWith(PAIR_PATH)) {
    return pairFrom(`${parsed.protocol}//${parsed.host}`, parsed.searchParams.get("code"), parsed.searchParams.get("label"));
  }
  return undefined;
}

/** expo-router path for a parsed link. */
export function routeFor(link: DeepLink): string {
  switch (link.kind) {
    case "pair":
      return `/pairing?url=${encodeURIComponent(link.url)}&code=${encodeURIComponent(link.code)}`;
    case "approval":
      return `/tasks?approval=${encodeURIComponent(link.id)}`;
    case "session":
      return `/?session=${encodeURIComponent(link.id)}`;
    case "result":
      return `/result/${encodeURIComponent(link.id)}`;
    case "job":
      return `/tasks?job=${encodeURIComponent(link.id)}`;
    case "tab":
      return link.name === "agent" ? "/" : `/${link.name}`;
  }
}
