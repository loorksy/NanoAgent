import type {
  Approval,
  ApprovalData,
  ApprovalStatus,
  ArtifactData,
  GatewayEvent,
  JobData,
  MessageContentPart,
  NotificationData,
  StateData,
  StructuredResult,
  TimelineEvent,
} from "./types.ts";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  ts: number;
  run?: string;
  streaming: boolean;
  parts?: MessageContentPart[];
}

export type TimelineStatus = "running" | "finished" | "failed";

export interface ToolTimelineEntry {
  id: string;
  kind: "tool";
  call_id: string;
  name: string;
  display?: string;
  status: TimelineStatus;
  started_at: number;
  run?: string;
  summary?: string;
  duration_ms?: number;
}

export interface SubagentTimelineEntry {
  id: string;
  kind: "subagent";
  subagent_id: string;
  role: string;
  display?: string;
  status: TimelineStatus;
  started_at: number;
  run?: string;
  summary?: string;
  duration_ms?: number;
}

export interface RetryTimelineEntry {
  id: string;
  kind: "retry";
  retry_id: string;
  state: "waiting" | "recovered" | "cleared" | "exhausted";
  attempt: number;
  error_kind: string;
  status: TimelineStatus;
  started_at: number;
  run?: string;
}

export type TimelineEntry = ToolTimelineEntry | SubagentTimelineEntry | RetryTimelineEntry;

/** One quiet line from entries that already exist. The label comes from the caller. */
function marked(label: string, mark: "…" | "✓"): string {
  const text = label.trim();
  if (mark === "…" && (text.endsWith("…") || text.endsWith("..."))) return text;
  if (mark === "✓" && text.endsWith("✓")) return text;
  return `${text} ${mark}`;
}

export function activityLine(
  entries: readonly TimelineEntry[],
  labelFor: (entry: TimelineEntry) => string,
): string {
  const parts: string[] = [];
  for (const entry of entries) {
    const label = labelFor(entry).trim();
    if (!label) continue;
    if (entry.status === "failed") parts.push(label);
    else if (entry.status === "finished") parts.push(marked(label, "✓"));
    else parts.push(marked(label, "…"));
  }
  return parts.join(" · ");
}

export interface ApprovalEntry extends ApprovalData {
  status: ApprovalStatus;
  ts: number;
  run?: string;
  session?: string;
}

export interface NotificationEntry extends NotificationData {
  id: string;
  ts: number;
}

export interface ArtifactEntry extends ArtifactData {
  id: string;
  ts: number;
  run?: string;
}

export interface SessionSnapshot {
  sessionId: string;
  messages: ChatMessage[];
  state: StateData;
  timeline: TimelineEntry[];
  results: StructuredResult[];
  artifacts: ArtifactEntry[];
  approvals: ApprovalEntry[];
  notifications: NotificationEntry[];
  jobs: Record<string, JobData>;
  lastEventId?: string;
  currentRun?: string;
}

export const IDLE_STATE: StateData = { state: "completed", outcome: "ok" };

export function initialSnapshot(sessionId: string, state: StateData = IDLE_STATE): SessionSnapshot {
  return {
    sessionId,
    messages: [],
    state,
    timeline: [],
    results: [],
    artifacts: [],
    approvals: [],
    notifications: [],
    jobs: {},
  };
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  const next = items.slice();
  next[index] = value;
  return next;
}

function upsertResult(results: StructuredResult[], result: StructuredResult): StructuredResult[] {
  const index = results.findIndex((item) => item.result_id === result.result_id);
  return index === -1 ? [...results, result] : replaceAt(results, index, result);
}

function applyDelta(snapshot: SessionSnapshot, event: Extract<GatewayEvent, { kind: "delta" }>): SessionSnapshot {
  const run = event.run;
  const messages = snapshot.messages;
  const last = messages[messages.length - 1];
  if (last && last.role === "assistant" && last.streaming && (run === undefined || last.run === run)) {
    const updated: ChatMessage = { ...last, text: last.text + event.data.text };
    return { ...snapshot, messages: replaceAt(messages, messages.length - 1, updated) };
  }
  const created: ChatMessage = {
    id: run ?? event.id,
    role: "assistant",
    text: event.data.text,
    ts: event.ts,
    streaming: true,
  };
  if (run !== undefined) created.run = run;
  const next: SessionSnapshot = { ...snapshot, messages: [...messages, created] };
  if (run !== undefined) next.currentRun = run;
  return next;
}

function finishStreaming(messages: ChatMessage[], run: string | undefined): ChatMessage[] {
  let changed = false;
  const next = messages.map((message) => {
    if (message.streaming && (run === undefined || message.run === run)) {
      changed = true;
      return { ...message, streaming: false };
    }
    return message;
  });
  return changed ? next : messages;
}

function applyTool(snapshot: SessionSnapshot, event: Extract<GatewayEvent, { kind: "tool" }>): SessionSnapshot {
  const { data } = event;
  const index = snapshot.timeline.findIndex(
    (entry) => entry.kind === "tool" && entry.call_id === data.call_id,
  );
  if (data.event === "started" || index === -1) {
    const entry: ToolTimelineEntry = {
      id: event.id,
      kind: "tool",
      call_id: data.call_id,
      name: data.name,
      status: data.event === "started" ? "running" : data.event === "failed" ? "failed" : "finished",
      started_at: event.ts,
    };
    if (data.display !== undefined) entry.display = data.display;
    if (event.run !== undefined) entry.run = event.run;
    if (data.summary !== undefined) entry.summary = data.summary;
    if (data.duration_ms !== undefined) entry.duration_ms = data.duration_ms;
    if (index === -1) return { ...snapshot, timeline: [...snapshot.timeline, entry] };
    return { ...snapshot, timeline: replaceAt(snapshot.timeline, index, entry) };
  }
  const existing = snapshot.timeline[index] as ToolTimelineEntry;
  const updated: ToolTimelineEntry = {
    ...existing,
    status: data.event === "failed" ? "failed" : "finished",
  };
  if (data.display !== undefined) updated.display = data.display;
  if (data.summary !== undefined) updated.summary = data.summary;
  if (data.duration_ms !== undefined) updated.duration_ms = data.duration_ms;
  return { ...snapshot, timeline: replaceAt(snapshot.timeline, index, updated) };
}

function subagentStatus(event: "started" | "finished" | "failed"): TimelineStatus {
  if (event === "started") return "running";
  if (event === "failed") return "failed";
  return "finished";
}

function applySubagent(
  snapshot: SessionSnapshot,
  event: Extract<GatewayEvent, { kind: "subagent" }>,
): SessionSnapshot {
  const { data } = event;
  const index = snapshot.timeline.findIndex(
    (entry) => entry.kind === "subagent" && entry.subagent_id === data.id,
  );
  if (index === -1) {
    const entry: SubagentTimelineEntry = {
      id: event.id,
      kind: "subagent",
      subagent_id: data.id,
      role: data.role,
      status: subagentStatus(data.event),
      started_at: event.ts,
    };
    if (event.run !== undefined) entry.run = event.run;
    if (data.summary !== undefined) entry.summary = data.summary;
    if (data.display !== undefined) entry.display = data.display;
    if (data.duration_ms !== undefined) entry.duration_ms = data.duration_ms;
    return { ...snapshot, timeline: [...snapshot.timeline, entry] };
  }
  const existing = snapshot.timeline[index] as SubagentTimelineEntry;
  const updated: SubagentTimelineEntry = {
    ...existing,
    status: subagentStatus(data.event),
  };
  if (data.summary !== undefined) updated.summary = data.summary;
  if (data.display !== undefined) updated.display = data.display;
  if (data.duration_ms !== undefined) updated.duration_ms = data.duration_ms;
  return { ...snapshot, timeline: replaceAt(snapshot.timeline, index, updated) };
}

function retryStatus(state: RetryTimelineEntry["state"]): TimelineStatus {
  if (state === "waiting") return "running";
  if (state === "exhausted") return "failed";
  return "finished";
}

function applyRetry(
  snapshot: SessionSnapshot,
  event: Extract<GatewayEvent, { kind: "retry" }>,
): SessionSnapshot {
  const { data } = event;
  const retryId = data.state === "cleared" ? "fallback" : `retry-${data.attempt}`;
  const index = snapshot.timeline.findIndex(
    (entry) => entry.kind === "retry" && entry.retry_id === retryId,
  );
  if (index === -1) {
    const entry: RetryTimelineEntry = {
      id: event.id,
      kind: "retry",
      retry_id: retryId,
      state: data.state,
      attempt: data.attempt,
      error_kind: data.error_kind,
      status: retryStatus(data.state),
      started_at: event.ts,
    };
    if (event.run !== undefined) entry.run = event.run;
    return { ...snapshot, timeline: [...snapshot.timeline, entry] };
  }
  const existing = snapshot.timeline[index] as RetryTimelineEntry;
  const updated: RetryTimelineEntry = {
    ...existing,
    state: data.state,
    attempt: data.attempt,
    error_kind: data.error_kind,
    status: retryStatus(data.state),
  };
  return { ...snapshot, timeline: replaceAt(snapshot.timeline, index, updated) };
}

function applyApproval(
  snapshot: SessionSnapshot,
  data: ApprovalData,
  ts: number,
  run: string | undefined,
  status: ApprovalStatus = "pending",
): SessionSnapshot {
  const index = snapshot.approvals.findIndex((item) => item.approval_id === data.approval_id);
  const existing = index === -1 ? undefined : snapshot.approvals[index];
  // The gateway repeats the approval event with its final status when it is resolved.
  const finalStatus = data.status ?? existing?.status ?? status;
  const entry: ApprovalEntry = {
    ...data,
    actions: data.actions ?? existing?.actions ?? ["confirm", "cancel"],
    status: finalStatus,
    ts,
    session: snapshot.sessionId,
  };
  if (run !== undefined) entry.run = run;
  const approvals =
    index === -1 ? [...snapshot.approvals, entry] : replaceAt(snapshot.approvals, index, entry);
  let state = snapshot.state;
  if (finalStatus === "pending" && state.state !== "waiting") {
    state = { state: "waiting", waiting_for: { kind: "approval", id: data.approval_id } };
  } else if (
    finalStatus !== "pending" &&
    state.state === "waiting" &&
    state.waiting_for?.kind === "approval" &&
    state.waiting_for.id === data.approval_id
  ) {
    state = { state: "working", phase: "thinking" };
  }
  return { ...snapshot, approvals, state };
}

/** Pure reducer: fold one gateway event into the snapshot. Duplicate/old ids are ignored. */
export function applyEvent(snapshot: SessionSnapshot, event: GatewayEvent): SessionSnapshot {
  if (snapshot.lastEventId !== undefined && event.id <= snapshot.lastEventId) return snapshot;
  let next: SessionSnapshot = { ...snapshot, lastEventId: event.id };
  if (event.run !== undefined && event.kind !== "end") next.currentRun = event.run;
  switch (event.kind) {
    case "delta":
      next = applyDelta(next, event);
      break;
    case "state":
      next.state = event.data;
      if (event.data.state === "completed") next.messages = finishStreaming(next.messages, event.run);
      break;
    case "tool":
      next = applyTool(next, event);
      break;
    case "subagent":
      next = applySubagent(next, event);
      break;
    case "retry":
      next = applyRetry(next, event);
      break;
    case "structured": {
      const result: StructuredResult = { ...event.data, session: event.session, ts: event.ts };
      next.results = upsertResult(next.results, result);
      if (event.data.type === "approval") {
        next = applyApproval(next, event.data.payload, event.ts, event.run);
      }
      break;
    }
    case "artifact": {
      const artifact: ArtifactEntry = { ...event.data, id: event.id, ts: event.ts };
      if (event.run !== undefined) artifact.run = event.run;
      next.artifacts = [...next.artifacts, artifact];
      break;
    }
    case "approval":
      next = applyApproval(next, event.data, event.ts, event.run);
      break;
    case "notification":
      next.notifications = [...next.notifications, { ...event.data, id: event.id, ts: event.ts }];
      break;
    case "job":
      next.jobs = { ...next.jobs, [event.data.job_id]: event.data };
      break;
    case "end":
      next.messages = finishStreaming(next.messages, event.data.run);
      if (next.state.state !== "completed") {
        next.state = { state: "completed", outcome: event.data.outcome };
      }
      if (next.currentRun === event.data.run) delete next.currentRun;
      break;
    default:
      break;
  }
  return next;
}

export function applyEvents(snapshot: SessionSnapshot, events: Iterable<GatewayEvent>): SessionSnapshot {
  let next = snapshot;
  for (const event of events) next = applyEvent(next, event);
  return next;
}

export function addUserMessage(
  snapshot: SessionSnapshot,
  text: string,
  options: { id?: string; ts?: number; parts?: MessageContentPart[] } = {},
): SessionSnapshot {
  const message: ChatMessage = {
    id: options.id ?? `local_${snapshot.messages.length + 1}_${options.ts ?? Date.now()}`,
    role: "user",
    text,
    ts: options.ts ?? Date.now(),
    streaming: false,
  };
  if (options.parts) message.parts = options.parts;
  return {
    ...snapshot,
    messages: [...snapshot.messages, message],
    state: { state: "working", phase: "queued" },
  };
}

/** Local optimistic update after `POST /approvals/{id}`; the gateway confirms via events. */
export function setApprovalStatus(
  snapshot: SessionSnapshot,
  approvalId: string,
  status: ApprovalStatus,
): SessionSnapshot {
  const index = snapshot.approvals.findIndex((item) => item.approval_id === approvalId);
  if (index === -1) return snapshot;
  const approvals = replaceAt(snapshot.approvals, index, { ...snapshot.approvals[index]!, status });
  let state = snapshot.state;
  const waiting = state.waiting_for;
  if (state.state === "waiting" && waiting?.kind === "approval" && waiting.id === approvalId) {
    state = { state: "working", phase: "thinking" };
  }
  return { ...snapshot, approvals, state };
}

export function pendingApprovals(snapshot: SessionSnapshot): ApprovalEntry[] {
  return snapshot.approvals.filter((item) => item.status === "pending");
}

/** Seed a snapshot from REST (`GET /state`, `/timeline`, `/approvals`) before streaming. */
export function hydrate(
  snapshot: SessionSnapshot,
  data: { state?: StateData; timeline?: TimelineEvent[]; approvals?: Approval[] },
): SessionSnapshot {
  let next = snapshot;
  if (data.timeline) {
    const base: SessionSnapshot = { ...next };
    delete base.lastEventId;
    next = applyEvents(base, data.timeline);
    if (snapshot.lastEventId !== undefined && (next.lastEventId ?? "") < snapshot.lastEventId) {
      next.lastEventId = snapshot.lastEventId;
    }
  }
  if (data.approvals) {
    for (const approval of data.approvals) {
      const index = next.approvals.findIndex((item) => item.approval_id === approval.approval_id);
      const entry: ApprovalEntry = {
        approval_id: approval.approval_id,
        type: approval.type,
        summary: approval.summary,
        expires_at: approval.expires_at,
        actions: ["confirm", "cancel"],
        status: approval.status,
        ts: approval.created_at ?? 0,
        session: approval.session ?? snapshot.sessionId,
      };
      if (approval.run) entry.run = approval.run;
      next = {
        ...next,
        approvals: index === -1 ? [...next.approvals, entry] : replaceAt(next.approvals, index, entry),
      };
    }
  }
  if (data.state) next = { ...next, state: data.state };
  return next;
}

export type Listener = (snapshot: SessionSnapshot) => void;

/** Minimal observable wrapper around the reducer, compatible with `useSyncExternalStore`. */
export class SessionStore {
  private snapshot: SessionSnapshot;
  private readonly listeners = new Set<Listener>();

  constructor(sessionId: string, snapshot?: SessionSnapshot) {
    this.snapshot = snapshot ?? initialSnapshot(sessionId);
  }

  getSnapshot = (): SessionSnapshot => this.snapshot;

  subscribe = (listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  update(updater: (snapshot: SessionSnapshot) => SessionSnapshot): void {
    const next = updater(this.snapshot);
    if (next === this.snapshot) return;
    this.snapshot = next;
    for (const listener of this.listeners) listener(next);
  }

  dispatch(event: GatewayEvent): void {
    this.update((snapshot) => applyEvent(snapshot, event));
  }

  addUserMessage(text: string, options?: { id?: string; ts?: number; parts?: MessageContentPart[] }): void {
    this.update((snapshot) => addUserMessage(snapshot, text, options));
  }
}
