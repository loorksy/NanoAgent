import { GatewayError, type GatewayClient } from "./client.ts";
import type { GatewayEvent } from "./types.ts";

export interface SseMessage {
  id?: string;
  event?: string;
  data: string;
  retry?: number;
}

/**
 * Incremental `text/event-stream` parser (WHATWG spec): feed arbitrary chunks, get complete
 * messages. Handles `\r\n`, `\n` and `\r` line endings, multi-line `data:`, comments and `retry:`.
 */
export class SseParser {
  private buffer = "";
  private id: string | undefined;
  private event: string | undefined;
  private data: string[] = [];
  private retry: number | undefined;
  /** Last `id:` seen, persisted across messages as the spec requires. */
  lastEventId: string | undefined;

  feed(chunk: string): SseMessage[] {
    this.buffer += chunk;
    const messages: SseMessage[] = [];
    let start = 0;
    for (;;) {
      const lf = this.buffer.indexOf("\n", start);
      const cr = this.buffer.indexOf("\r", start);
      let end: number;
      let skip: number;
      if (cr !== -1 && (lf === -1 || cr < lf)) {
        if (cr === this.buffer.length - 1) break;
        end = cr;
        skip = this.buffer[cr + 1] === "\n" ? 2 : 1;
      } else if (lf !== -1) {
        end = lf;
        skip = 1;
      } else {
        break;
      }
      const line = this.buffer.slice(start, end);
      start = end + skip;
      const message = this.processLine(line);
      if (message) messages.push(message);
    }
    this.buffer = this.buffer.slice(start);
    return messages;
  }

  private processLine(line: string): SseMessage | undefined {
    if (line === "") return this.dispatch();
    if (line.startsWith(":")) return undefined;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    switch (field) {
      case "data":
        this.data.push(value);
        break;
      case "id":
        if (!value.includes("\u0000")) {
          this.id = value;
          this.lastEventId = value;
        }
        break;
      case "event":
        this.event = value;
        break;
      case "retry": {
        const parsed = Number.parseInt(value, 10);
        if (Number.isFinite(parsed) && parsed >= 0 && /^\d+$/.test(value)) this.retry = parsed;
        break;
      }
      default:
        break;
    }
    return undefined;
  }

  private dispatch(): SseMessage | undefined {
    const hasData = this.data.length > 0;
    const message: SseMessage | undefined = hasData
      ? { data: this.data.join("\n") }
      : this.retry !== undefined
        ? { data: "" }
        : undefined;
    if (message) {
      if (this.id !== undefined) message.id = this.id;
      if (this.event !== undefined) message.event = this.event;
      if (this.retry !== undefined) message.retry = this.retry;
    }
    this.data = [];
    this.event = undefined;
    this.retry = undefined;
    return message;
  }
}

export function parseGatewayEvent(raw: string): GatewayEvent | undefined {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return undefined;
  }
  if (!parsed || typeof parsed !== "object") return undefined;
  const candidate = parsed as Record<string, unknown>;
  if (typeof candidate["kind"] !== "string" || typeof candidate["id"] !== "string") return undefined;
  if (!candidate["data"] || typeof candidate["data"] !== "object") return undefined;
  return candidate as unknown as GatewayEvent;
}

export interface BackoffOptions {
  initialMs: number;
  maxMs: number;
  factor: number;
}

export const DEFAULT_BACKOFF: BackoffOptions = { initialMs: 1000, maxMs: 30_000, factor: 2 };

export type SubscribeStatus = "connecting" | "open" | "reconnecting" | "closed";

export interface SubscribeOptions {
  /** Resume after this event id (sent as `?after=` and `Last-Event-ID`). */
  after?: string;
  signal?: AbortSignal;
  backoff?: Partial<BackoffOptions>;
  /** Give up after this many consecutive failed connections (default: unlimited). */
  maxRetries?: number;
  /** Injected for tests; defaults to a timer that resolves early on abort. */
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  onStatus?: (status: SubscribeStatus, error?: unknown) => void;
}

export function defaultSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve();
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort(): void {
      clearTimeout(timer);
      resolve();
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

function isFatalStatus(status: number): boolean {
  return status === 401 || status === 403 || status === 404;
}

async function* readBody(response: Response): AsyncGenerator<string> {
  const body = response.body;
  if (!body || typeof body.getReader !== "function") {
    yield await response.text();
    return;
  }
  const reader = body.getReader();
  const decoder = new TextDecoder();
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value) yield decoder.decode(value, { stream: true });
    }
    const tail = decoder.decode();
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

/**
 * Subscribe to `GET /sessions/{id}/events` as an async iterator of `GatewayEvent`.
 * Reconnects with exponential backoff and resumes from the last seen event id, so a
 * 30-second network drop loses no events (07 §11).
 */
export async function* subscribe(
  client: GatewayClient,
  sessionId: string,
  options: SubscribeOptions = {},
): AsyncGenerator<GatewayEvent, void, undefined> {
  const backoff: BackoffOptions = { ...DEFAULT_BACKOFF, ...options.backoff };
  const sleep = options.sleep ?? defaultSleep;
  const signal = options.signal;
  let after = options.after;
  let attempt = 0;
  let delayMs = backoff.initialMs;
  let serverRetry: number | undefined;

  const notify = (status: SubscribeStatus, error?: unknown): void => {
    options.onStatus?.(status, error);
  };

  while (!signal?.aborted) {
    notify(attempt === 0 ? "connecting" : "reconnecting");
    let failed = false;
    try {
      const extra: Record<string, string> = { Accept: "text/event-stream" };
      if (after) extra["Last-Event-ID"] = after;
      const headers = await client.headers(extra);
      const init: RequestInit = { method: "GET", headers };
      if (signal) init.signal = signal;
      const response = await client.fetchStream(client.eventsUrl(sessionId, after), init);
      if (!response.ok) {
        if (isFatalStatus(response.status)) {
          const error = new GatewayError(response.status, undefined, "error.sse_unauthorized");
          notify("closed", error);
          throw error;
        }
        failed = true;
      } else {
        notify("open");
        const parser = new SseParser();
        for await (const chunk of readBody(response)) {
          for (const message of parser.feed(chunk)) {
            if (message.retry !== undefined) serverRetry = message.retry;
            if (!message.data) continue;
            const event = parseGatewayEvent(message.data);
            if (!event) continue;
            after = message.id ?? event.id;
            attempt = 0;
            delayMs = backoff.initialMs;
            yield event;
            if (signal?.aborted) break;
          }
        }
      }
    } catch (error) {
      if (signal?.aborted) break;
      if (error instanceof GatewayError && isFatalStatus(error.status)) throw error;
      failed = true;
    }
    if (signal?.aborted) break;
    if (failed) {
      attempt += 1;
      if (options.maxRetries !== undefined && attempt > options.maxRetries) {
        notify("closed");
        return;
      }
    }
    const wait = serverRetry ?? delayMs;
    serverRetry = undefined;
    await sleep(wait, signal);
    delayMs = Math.min(delayMs * backoff.factor, backoff.maxMs);
  }
  notify("closed");
}
