import { describe, expect, test } from "bun:test";

import {
  SessionStore,
  addUserMessage,
  applyEvent,
  applyEvents,
  hydrate,
  initialSnapshot,
  pendingApprovals,
  setApprovalStatus,
} from "../src/store.ts";
import type { GatewayEvent } from "../src/types.ts";

let counter = 0;
function ev<K extends GatewayEvent["kind"]>(
  kind: K,
  data: Extract<GatewayEvent, { kind: K }>["data"],
  run = "r_1",
): Extract<GatewayEvent, { kind: K }> {
  counter += 1;
  return {
    id: `01H${String(counter).padStart(6, "0")}`,
    session: "s_1",
    run,
    ts: 1_700_000_000_000 + counter,
    kind,
    data,
  } as Extract<GatewayEvent, { kind: K }>;
}

describe("applyEvent", () => {
  test("working → waiting on approval → completed", () => {
    let snap = addUserMessage(initialSnapshot("s_1"), "buy gold?", { id: "u1", ts: 1 });
    expect(snap.state).toEqual({ state: "working", phase: "queued" });

    snap = applyEvent(snap, ev("state", { state: "working", phase: "thinking" }));
    expect(snap.state.phase).toBe("thinking");

    snap = applyEvent(
      snap,
      ev("approval", {
        approval_id: "a1",
        type: "execution",
        summary: "BUY 0.1 XAUUSD",
        expires_at: 2,
        actions: ["confirm", "cancel"],
      }),
    );
    expect(snap.state).toEqual({ state: "waiting", waiting_for: { kind: "approval", id: "a1" } });
    expect(pendingApprovals(snap).map((a) => a.approval_id)).toEqual(["a1"]);

    snap = applyEvent(
      snap,
      ev("state", { state: "waiting", waiting_for: { kind: "approval", id: "a1" } }),
    );
    expect(snap.state.state).toBe("waiting");

    snap = setApprovalStatus(snap, "a1", "confirmed");
    expect(snap.approvals[0]?.status).toBe("confirmed");
    expect(snap.state.state).toBe("working");

    snap = applyEvent(snap, ev("state", { state: "completed", outcome: "ok" }));
    snap = applyEvent(snap, ev("end", { run: "r_1", outcome: "ok" }));
    expect(snap.state).toEqual({ state: "completed", outcome: "ok" });
    expect(snap.currentRun).toBeUndefined();
  });

  test("deltas accumulate into one streaming assistant message per run and end finalises it", () => {
    let snap = initialSnapshot("s_1");
    snap = applyEvents(snap, [ev("delta", { text: "Gold " }), ev("delta", { text: "is up" })]);
    expect(snap.messages).toHaveLength(1);
    expect(snap.messages[0]).toMatchObject({ role: "assistant", text: "Gold is up", streaming: true, run: "r_1" });
    snap = applyEvent(snap, ev("end", { run: "r_1", outcome: "ok" }));
    expect(snap.messages[0]?.streaming).toBe(false);
    snap = applyEvent(snap, ev("delta", { text: "Second" }, "r_2"));
    expect(snap.messages).toHaveLength(2);
    expect(snap.messages[1]?.run).toBe("r_2");
  });

  test("end without explicit completed state sets completed with outcome", () => {
    let snap = applyEvent(initialSnapshot("s_1"), ev("state", { state: "working", phase: "tool:web" }));
    snap = applyEvent(snap, ev("end", { run: "r_1", outcome: "cancelled" }));
    expect(snap.state).toEqual({ state: "completed", outcome: "cancelled" });
  });

  test("tool started/finished collapse into one timeline entry", () => {
    let snap = initialSnapshot("s_1");
    snap = applyEvent(snap, ev("tool", { event: "started", name: "web_search", call_id: "c1" }));
    expect(snap.timeline).toHaveLength(1);
    expect(snap.timeline[0]).toMatchObject({ kind: "tool", status: "running", name: "web_search" });
    snap = applyEvent(
      snap,
      ev("tool", { event: "finished", name: "web_search", call_id: "c1", summary: "3 results", duration_ms: 420 }),
    );
    expect(snap.timeline).toHaveLength(1);
    expect(snap.timeline[0]).toMatchObject({ status: "finished", summary: "3 results", duration_ms: 420 });
    snap = applyEvent(snap, ev("tool", { event: "failed", name: "exec", call_id: "c2", summary: "timeout" }));
    expect(snap.timeline[1]).toMatchObject({ kind: "tool", status: "failed", call_id: "c2" });
  });

  test("subagent lifecycle and structured/artifact/notification/job events", () => {
    let snap = initialSnapshot("s_1");
    snap = applyEvent(snap, ev("subagent", { event: "started", id: "sa1", role: "bear" }));
    snap = applyEvent(snap, ev("subagent", { event: "finished", id: "sa1", role: "bear", summary: "no" }));
    expect(snap.timeline).toEqual([
      expect.objectContaining({ kind: "subagent", subagent_id: "sa1", status: "finished", summary: "no" }),
    ]);
    snap = applyEvent(
      snap,
      ev("structured", {
        type: "risk",
        result_id: "res1",
        payload: { risk_pct: 1, lot: 0.1, rr: 2, daily_dd_used_pct: 0.5, open_positions: 0, blockers: [] },
      }),
    );
    snap = applyEvent(
      snap,
      ev("structured", {
        type: "risk",
        result_id: "res1",
        payload: { risk_pct: 1, lot: 0.2, rr: 2, daily_dd_used_pct: 0.5, open_positions: 0, blockers: [] },
      }),
    );
    expect(snap.results).toHaveLength(1);
    expect(snap.results[0]?.type === "risk" && snap.results[0].payload.lot).toBe(0.2);
    snap = applyEvent(snap, ev("artifact", { artifact_id: "art", mime: "image/png", url: "/a.png", title: "chart" }));
    snap = applyEvent(snap, ev("notification", { level: "warning", title: "t", body: "b" }));
    snap = applyEvent(
      snap,
      ev("job", { job_id: "j1", kind: "goal", status: "working", progress: { ui_summary: "scan" } }),
    );
    expect(snap.artifacts).toHaveLength(1);
    expect(snap.notifications[0]?.level).toBe("warning");
    expect(snap.jobs["j1"]?.progress).toEqual({ ui_summary: "scan" });
  });

  test("structured approval result registers a pending approval", () => {
    const snap = applyEvent(
      initialSnapshot("s_1"),
      ev("structured", {
        type: "approval",
        result_id: "res2",
        payload: {
          approval_id: "a9",
          type: "close",
          summary: "close all",
          expires_at: 5,
          actions: ["confirm", "cancel"],
          permission_level: "propose",
        },
      }),
    );
    expect(pendingApprovals(snap)).toHaveLength(1);
    expect(snap.state.state).toBe("waiting");
  });

  test("duplicate and out-of-order replayed events are ignored", () => {
    const first = ev("delta", { text: "a" });
    const second = ev("delta", { text: "b" });
    let snap = applyEvents(initialSnapshot("s_1"), [first, second]);
    snap = applyEvents(snap, [first, second]);
    expect(snap.messages[0]?.text).toBe("ab");
    expect(snap.lastEventId).toBe(second.id);
  });

  test("hydrate seeds state, timeline and approvals from REST", () => {
    const tool = ev("tool", { event: "finished", name: "x", call_id: "c" });
    const snap = hydrate(initialSnapshot("s_1"), {
      state: { state: "waiting", waiting_for: { kind: "approval", id: "a1" } },
      timeline: [tool],
      approvals: [
        {
          id: "a1",
          approval_id: "a1",
          type: "execution",
          summary: "s",
          expires_at: 1,
          status: "pending",
          session: "s_1",
          run: null,
          created_at: 5,
          resolved_at: null,
          decision: null,
          source_id: null,
          details: {},
        },
      ],
    });
    expect(snap.timeline).toHaveLength(1);
    expect(snap.lastEventId).toBe(tool.id);
    expect(snap.approvals[0]?.status).toBe("pending");
    expect(snap.approvals[0]?.actions).toEqual(["confirm", "cancel"]);
    expect(snap.state.state).toBe("waiting");
  });

  test("approval event with a final status resolves the wait", () => {
    let snap = initialSnapshot("s_1", { state: "working", phase: "thinking" });
    snap = applyEvent(
      snap,
      ev("approval", { approval_id: "a1", type: "execution", summary: "s", expires_at: 9, status: "pending" }),
    );
    expect(snap.state).toEqual({ state: "waiting", waiting_for: { kind: "approval", id: "a1" } });
    snap = applyEvent(
      snap,
      ev("approval", { approval_id: "a1", type: "execution", summary: "s", expires_at: 9, status: "confirmed", actions: [] }),
    );
    expect(snap.approvals[0]?.status).toBe("confirmed");
    expect(snap.approvals[0]?.actions).toEqual([]);
    expect(snap.state.state).toBe("working");
  });
});

describe("SessionStore", () => {
  test("notifies listeners on change only", () => {
    const store = new SessionStore("s_1");
    const seen: number[] = [];
    const unsubscribe = store.subscribe((snap) => seen.push(snap.messages.length));
    store.addUserMessage("hi");
    store.dispatch(ev("delta", { text: "yo" }));
    const same = store.getSnapshot();
    store.update((snap) => snap);
    expect(store.getSnapshot()).toBe(same);
    unsubscribe();
    store.addUserMessage("again");
    expect(seen).toEqual([1, 2]);
  });
});
