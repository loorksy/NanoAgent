import type { GatewayClient } from "./client.ts";
import { DEFAULT_BACKOFF, defaultSleep, type BackoffOptions } from "./sse.ts";
import type { ApprovalDecision, GatewayEvent, MessageContentPart, WsClientMessage, WsServerMessage } from "./types.ts";

/** Structural subset of the WHATWG WebSocket used here (works in RN, browsers, Bun, `ws`). */
export interface WebSocketLike {
  readonly readyState: number;
  onopen: ((event: unknown) => void) | null;
  onclose: ((event: unknown) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onmessage: ((event: { data: unknown }) => void) | null;
  send(data: string): void;
  close(code?: number, reason?: string): void;
}

export type WebSocketFactory = (url: string) => WebSocketLike;

export type WsStatus = "connecting" | "open" | "reconnecting" | "closed";

export interface GatewayWebSocketOptions {
  /** Defaults to `globalThis.WebSocket`. */
  factory?: WebSocketFactory;
  backoff?: Partial<BackoffOptions>;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  /** Interval for `ping` frames; `0` disables (default 25s). */
  pingIntervalMs?: number;
  onStatus?: (status: WsStatus, error?: unknown) => void;
  onError?: (error: WsServerMessage & { type: "error" }) => void;
}

export type EventListener = (event: GatewayEvent) => void;

const OPEN = 1;

function defaultFactory(url: string): WebSocketLike {
  const ctor = (globalThis as { WebSocket?: new (url: string) => WebSocketLike }).WebSocket;
  if (!ctor) throw new Error("No WebSocket implementation available; pass `factory`");
  return new ctor(url);
}

export function parseServerMessage(raw: unknown): WsServerMessage | undefined {
  if (typeof raw !== "string") return undefined;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return undefined;
  }
  if (!parsed || typeof parsed !== "object") return undefined;
  const candidate = parsed as Record<string, unknown>;
  if (typeof candidate["type"] !== "string") return undefined;
  return candidate as unknown as WsServerMessage;
}

/**
 * Multiplexed `/ws/v2` client: one socket per client, sessions selected by the `session`
 * field. Re-subscribes with the last seen event id per session after reconnecting.
 * The bearer token is passed as a `token` query parameter because RN/browser sockets
 * cannot set request headers.
 */
export class GatewayWebSocket {
  private socket: WebSocketLike | undefined;
  private readonly listeners = new Set<EventListener>();
  private readonly subscriptions = new Map<string, string | undefined>();
  private readonly abort = new AbortController();
  private readonly backoff: BackoffOptions;
  private readonly sleep: (ms: number, signal?: AbortSignal) => Promise<void>;
  private readonly factory: WebSocketFactory;
  private readonly pingIntervalMs: number;
  private pingTimer: ReturnType<typeof setInterval> | undefined;
  private queue: WsClientMessage[] = [];
  private attempt = 0;
  private running = false;

  constructor(
    private readonly client: GatewayClient,
    private readonly options: GatewayWebSocketOptions = {},
  ) {
    this.backoff = { ...DEFAULT_BACKOFF, ...options.backoff };
    this.sleep = options.sleep ?? defaultSleep;
    this.factory = options.factory ?? defaultFactory;
    this.pingIntervalMs = options.pingIntervalMs ?? 25_000;
  }

  onEvent(listener: EventListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  get isOpen(): boolean {
    return this.socket?.readyState === OPEN;
  }

  async connect(): Promise<void> {
    if (this.running) return;
    this.running = true;
    void this.loop();
  }

  close(): void {
    this.running = false;
    this.abort.abort();
    this.stopPing();
    this.socket?.close(1000, "client_close");
    this.socket = undefined;
    this.options.onStatus?.("closed");
  }

  /** Subscriptions are replayed on every (re)connect, so they are only sent live when open. */
  subscribe(session: string, after?: string): void {
    this.subscriptions.set(session, after);
    if (!this.isOpen) return;
    const message: WsClientMessage = { type: "subscribe", session };
    if (after !== undefined) message.after = after;
    this.send(message);
  }

  unsubscribe(session: string): void {
    this.subscriptions.delete(session);
    if (this.isOpen) this.send({ type: "unsubscribe", session });
  }

  sendMessage(session: string, text: string, parts?: MessageContentPart[], requestId?: string): void {
    const message: WsClientMessage = { type: "send", session, text };
    if (parts) message.parts = parts;
    if (requestId !== undefined) message.request_id = requestId;
    this.send(message);
  }

  cancel(session: string): void {
    this.send({ type: "cancel", session });
  }

  approve(approvalId: string, decision: ApprovalDecision, session?: string): void {
    const message: WsClientMessage = { type: "approve", approval_id: approvalId, decision };
    if (session !== undefined) message.session = session;
    this.send(message);
  }

  ping(): void {
    this.send({ type: "ping", ts: Date.now() });
  }

  send(message: WsClientMessage): void {
    const socket = this.socket;
    if (socket && socket.readyState === OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      this.queue.push(message);
    }
  }

  private async loop(): Promise<void> {
    let delayMs = this.backoff.initialMs;
    while (this.running && !this.abort.signal.aborted) {
      this.options.onStatus?.(this.attempt === 0 ? "connecting" : "reconnecting");
      const closed = await this.openOnce();
      if (!this.running) break;
      this.attempt += 1;
      await this.sleep(closed.clean ? this.backoff.initialMs : delayMs, this.abort.signal);
      delayMs = Math.min(delayMs * this.backoff.factor, this.backoff.maxMs);
    }
  }

  private async openOnce(): Promise<{ clean: boolean }> {
    const token = await this.client.resolveToken();
    const url = new URL(this.client.wsUrl());
    if (token) url.searchParams.set("token", token);
    let socket: WebSocketLike;
    try {
      socket = this.factory(url.toString());
    } catch (error) {
      this.options.onStatus?.("closed", error);
      return { clean: false };
    }
    this.socket = socket;
    return new Promise((resolve) => {
      let settled = false;
      const finish = (clean: boolean): void => {
        if (settled) return;
        settled = true;
        this.stopPing();
        if (this.socket === socket) this.socket = undefined;
        resolve({ clean });
      };
      socket.onopen = () => {
        this.attempt = 0;
        this.options.onStatus?.("open");
        for (const [session, after] of this.subscriptions) {
          const message: WsClientMessage = { type: "subscribe", session };
          if (after !== undefined) message.after = after;
          socket.send(JSON.stringify(message));
        }
        const pending = this.queue;
        this.queue = [];
        for (const message of pending) socket.send(JSON.stringify(message));
        this.startPing();
      };
      socket.onmessage = (raw) => {
        const message = parseServerMessage(raw.data);
        if (!message) return;
        if (message.type === "event") {
          this.subscriptions.set(message.event.session, message.event.id);
          for (const listener of this.listeners) listener(message.event);
        } else if (message.type === "error") {
          this.options.onError?.(message);
        }
      };
      socket.onerror = (error) => {
        this.options.onStatus?.("reconnecting", error);
      };
      socket.onclose = () => finish(true);
    });
  }

  private startPing(): void {
    this.stopPing();
    if (this.pingIntervalMs <= 0) return;
    this.pingTimer = setInterval(() => this.ping(), this.pingIntervalMs);
  }

  private stopPing(): void {
    if (this.pingTimer !== undefined) {
      clearInterval(this.pingTimer);
      this.pingTimer = undefined;
    }
  }
}
