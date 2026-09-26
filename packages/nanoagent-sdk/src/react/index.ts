import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import type { GatewayClient } from "../client.ts";
import { subscribe, type SubscribeStatus } from "../sse.ts";
import {
  SessionStore,
  hydrate,
  setApprovalStatus,
  type ApprovalEntry,
  type SessionSnapshot,
  type TimelineEntry,
} from "../store.ts";
import type {
  Approval,
  ApprovalDecision,
  ApprovalStatus,
  Job,
  MessageContentPart,
  StateData,
} from "../types.ts";

export interface UseSessionOptions {
  /** Skip the REST hydration (`/state`, `/timeline`, `/approvals`) before streaming. */
  hydrate?: boolean;
  enabled?: boolean;
}

export interface SessionController {
  store: SessionStore;
  snapshot: SessionSnapshot;
  status: SubscribeStatus;
  error: unknown;
  send: (text: string, parts?: MessageContentPart[]) => Promise<void>;
  cancel: () => Promise<void>;
  decide: (approvalId: string, decision: ApprovalDecision) => Promise<void>;
}

export function useSessionStore(sessionId: string | undefined): SessionStore {
  const ref = useRef<SessionStore | undefined>(undefined);
  if (!ref.current || (sessionId !== undefined && ref.current.getSnapshot().sessionId !== sessionId)) {
    ref.current = new SessionStore(sessionId ?? "");
  }
  return ref.current;
}

export function useSnapshot(store: SessionStore): SessionSnapshot {
  return useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
}

/** Hydrate + stream a session; one SSE connection per mounted hook. */
export function useSession(
  client: GatewayClient,
  sessionId: string | undefined,
  options: UseSessionOptions = {},
): SessionController {
  const store = useSessionStore(sessionId);
  const snapshot = useSnapshot(store);
  const [status, setStatus] = useState<SubscribeStatus>("closed");
  const [error, setError] = useState<unknown>(undefined);
  const enabled = options.enabled ?? true;
  const shouldHydrate = options.hydrate ?? true;

  useEffect(() => {
    if (!sessionId || !enabled) return;
    const controller = new AbortController();
    let cancelled = false;
    (async () => {
      try {
        if (shouldHydrate) {
          const [state, timeline, approvals] = await Promise.all([
            client.getState(sessionId),
            client.getTimeline(sessionId),
            client.listApprovals("pending"),
          ]);
          if (cancelled) return;
          store.update((current) =>
            hydrate(current, {
              state,
              timeline: timeline.events,
              approvals: approvals.filter((item) => !item.session || item.session === sessionId),
            }),
          );
        }
        const after = store.getSnapshot().lastEventId;
        const iterator = subscribe(client, sessionId, {
          ...(after !== undefined ? { after } : {}),
          signal: controller.signal,
          onStatus: (next, err) => {
            if (cancelled) return;
            setStatus(next);
            if (err !== undefined) setError(err);
          },
        });
        for await (const event of iterator) {
          if (cancelled) break;
          store.dispatch(event);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [client, sessionId, enabled, shouldHydrate, store]);

  const send = useCallback(
    async (text: string, parts?: MessageContentPart[]) => {
      if (!sessionId) return;
      store.addUserMessage(text, parts ? { parts } : undefined);
      try {
        await client.sendMessage(sessionId, parts ? { text, parts } : { text });
      } catch (err) {
        setError(err);
        throw err;
      }
    },
    [client, sessionId, store],
  );

  const cancel = useCallback(async () => {
    if (!sessionId) return;
    await client.cancel(sessionId);
  }, [client, sessionId]);

  const decide = useCallback(
    async (approvalId: string, decision: ApprovalDecision) => {
      const response = await client.decideApproval(approvalId, decision);
      store.update((current) => setApprovalStatus(current, approvalId, response.status));
    },
    [client, store],
  );

  return useMemo(
    () => ({ store, snapshot, status, error, send, cancel, decide }),
    [store, snapshot, status, error, send, cancel, decide],
  );
}

export function useAgentState(store: SessionStore): StateData {
  return useSnapshot(store).state;
}

export function useTimeline(store: SessionStore): TimelineEntry[] {
  return useSnapshot(store).timeline;
}

export function useSessionApprovals(store: SessionStore): ApprovalEntry[] {
  return useSnapshot(store).approvals;
}

interface PollingOptions {
  pollMs?: number;
  enabled?: boolean;
}

interface Resource<T> {
  data: T;
  loading: boolean;
  error: unknown;
  refresh: () => Promise<void>;
}

function usePolledResource<T>(
  loader: () => Promise<T>,
  initial: T,
  options: PollingOptions,
): Resource<T> & { setData: (updater: (current: T) => T) => void } {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(undefined);
  const enabled = options.enabled ?? true;
  const pollMs = options.pollMs ?? 0;
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await loaderRef.current();
      setData(next);
      setError(undefined);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
    if (pollMs <= 0) return;
    const timer = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(timer);
  }, [enabled, pollMs, refresh]);

  const update = useCallback((updater: (current: T) => T) => setData(updater), []);
  return { data, loading, error, refresh, setData: update };
}

export interface JobsController extends Resource<Job[]> {
  pause: (id: string) => Promise<void>;
  resume: (id: string) => Promise<void>;
  cancel: (id: string) => Promise<void>;
}

export function useJobs(client: GatewayClient, options: PollingOptions = {}): JobsController {
  const resource = usePolledResource(() => client.listJobs(), [] as Job[], options);
  const { setData } = resource;
  const replace = useCallback(
    (job: Job) => setData((jobs) => jobs.map((item) => (item.job_id === job.job_id ? job : item))),
    [setData],
  );
  const pause = useCallback(async (id: string) => replace(await client.pauseJob(id)), [client, replace]);
  const resume = useCallback(async (id: string) => replace(await client.resumeJob(id)), [client, replace]);
  const cancel = useCallback(
    async (id: string) => {
      const result = await client.cancelJob(id);
      setData((jobs) =>
        jobs.map((item) => (item.job_id === result.job_id ? { ...item, status: result.status } : item)),
      );
    },
    [client, setData],
  );
  return { ...resource, pause, resume, cancel };
}

export interface ApprovalsController extends Resource<Approval[]> {
  decide: (id: string, decision: ApprovalDecision) => Promise<void>;
}

export function useApprovals(
  client: GatewayClient,
  options: PollingOptions & { status?: ApprovalStatus } = {},
): ApprovalsController {
  const status = options.status ?? "pending";
  const resource = usePolledResource(() => client.listApprovals(status), [] as Approval[], options);
  const { setData } = resource;
  const decide = useCallback(
    async (id: string, decision: ApprovalDecision) => {
      const response = await client.decideApproval(id, decision);
      setData((items) =>
        items.map((item) => (item.approval_id === id ? { ...item, status: response.status } : item)),
      );
    },
    [client, setData],
  );
  return { ...resource, decide };
}
