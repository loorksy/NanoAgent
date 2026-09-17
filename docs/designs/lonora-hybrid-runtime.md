# Lonora Unified Agent Loop

> Saved: 2026-09-17
> Status: **PROPOSAL — awaiting sign-off** (no implementation in this PR)
> Branch: `cursor/unified-agent-loop-design-f9de`
> Supersedes: the 2026-09-13 "Hybrid Runtime" plan in this file (Phases H–M).
> That plan claimed a dynamic agentic planner. The code that shipped is a
> regex classifier plus a hardcoded mode map. This document describes the
> architecture we actually have, then the unified loop that should replace
> the routing layers — without weakening Hard Law.

This is a design proposal only. Do not implement until the **Open Questions**
section is signed off.

---

## 1. Why this document exists

`docs/designs/lonora-hybrid-runtime.md` (this file, previous revision) described:

```
Dynamic Agentic Planner  +  Deterministic Trading Kernel
```

and said `TurnPlanner` would decide which evidence nodes to run, how many
subagents to spawn, and which artifacts to emit.

What landed in the tree is different:

| Claim in the old doc | What the code actually does |
|----------------------|-----------------------------|
| Dynamic planner | `intent_router.py` regex / keyword classification |
| Planner expands with reasoning | `turn_planner.py` `if/elif` over 10 `TurnMode` literals |
| Dynamic DAG per turn | Mode → fixed node tuple (`MARKET_DATA_NODES`, `FULL_ANALYSIS_NODES`, …) |
| One executor | Two paths: `turn_executor.py` "light" vs `orchestrator.py` "full" |
| Policy Guard wraps a reasoning plan | `validate_turn_plan()` normalizes a static `TurnPlan` |

The Evidence Node graph (`nanobot/trading/evidence/`) is real and should stay.
The trading kernel (synthesizer, gates, store, state machine) is real and must
stay frozen. The **routing layers** that pretend to be a planner are what this
redesign replaces.

---

## 2. Honest current architecture

There are **two live entry paths** today, selected by env flags, plus a
third HTTP entry that bypasses both.

```
Operator message
    │
    ├─ LONORA_AGENT_FIRST=true (DEFAULT in production)
    │     AgentLoop skips try_gold_fast_path
    │     LLM sees coarse tools:
    │       get_gold_quote | capture_gold_chart | get_live_recommendation
    │       manage_trading_plan | analyze_gold | run_trading_team
    │     analyze_gold → run_unified_chart_agent (full graph, no TurnPlan)
    │
    └─ LONORA_AGENT_FIRST=false (legacy fast-path)
          route_intent(regex) → plan_turn(if/elif) → Policy Guard
          ├─ light modes → turn_executor.execute_light_path()
          └─ full_analysis / team_swarm → orchestrator.run_unified_chart_agent()
```

HTTP `/api/trading/analyze` and swarm/debate finals still call
`run_unified_chart_agent` directly.

### 2.1 What each routing file does

**`intent_router.py`** — not a planner. `route_intent()` scans
`operator_keywords` regexes in a fixed order (chart → team → recommend →
analysis → price → gold mention → `general_chat`) and returns an
`IntentKind` plus a confidence float.

**`turn_planner.py`** — not a reasoning planner. `_plan_turn_core()` maps
intent + `active_recommendation_live` onto one of ten `TurnMode` values:

`full_analysis`, `recommendation_followup`, `recommendation_supersede`,
`specialist`, `conversation`, `reevaluation`, `market_data_only`,
`chart_capture`, `team_swarm`, `gate_report`.

Each mode hardcodes `nodes`, `tools`, `emit_stages`, and `run_kernel`.
`apply_capability_plan()` then overlays another regex layer (Phase L
capability cards) that mutates nodes / team preset / spawn budget.

**`node_planner.py`** — one more keyword check (`wants_quick_analysis`)
that drops `visual_capture` from a full-analysis plan.

**`turn_executor.py`** — hand-written "light path" for
`market_data_only`, `chart_capture`, `recommendation_followup`,
`recommendation_supersede`. Independently rebuilds locale resolution,
evidence execution, artifact generation, and outbound metadata.

**`orchestrator.py` (`run_unified_chart_agent`)** — "full path": evidence
graph → `run_final_decision_synthesizer` → G1–G20 gate chain → store →
artifacts. Duplicates locale, `route_intent` (again, for artifact kind),
follow-up grading, and artifact application.

**`fast_path.py` (`try_gold_fast_path`)** — the glue: `plan_turn()` then
dispatches light vs full vs gate-report. Also owns supersede
approve/reject button handling.

**`policy_guard.py`** — validates a `TurnPlan` against known node ids,
clamps spawn budget, injects `SYNTHESIS_REQUIRED_NODES` for synthesis
modes, and under `LONORA_PLANNER_SHADOW=true` (default) **expands
synthesis plans back to the full graph**. Shadow here means "ignore the
subset and run everything", not "compare two systems".

### 2.2 What already works and must be kept

| Subsystem | Role | Constraint |
|-----------|------|------------|
| `evidence/` | `EvidenceNode` + layered `EvidenceGraph` executor | Keep as the **implementation** of evidence tools. Do not replace. |
| `agents/synthesizer.py` | Sole BUY/SELL authority | Only `run_final_decision_synthesizer` may emit buy/sell. |
| `gates/*.py` | G1–G20 chain + G7 reprice | Block or confidence-delta only; **never flip side**. |
| `recommendations/store.py` | Persistence | Unchanged. Already no-ops a second live rec per session. |
| `recommendations/state_machine.py` | Plan FSM | Unchanged. |
| `gold.py` | XAUUSD-only coerce | Unchanged. |
| `mt5_execution` tools | HITL propose → confirm | Unchanged. Analysis path never auto-sends (playbook 182 excluded). |
| `gold_intent_runtime_context` | Live-plan hint for the LLM | Keep; it is already "no keyword routing". |
| `skills/gold-trading/SKILL.md` | Operator-facing doctrine | Update tool names after implementation; doctrine stays. |

### 2.3 Agent-first is not the unified loop

`LONORA_AGENT_FIRST=true` (default) already lets the model pick among
**coarse** tools. That is progress over regex hijack, but it is not the
goal of this redesign:

- `get_gold_quote` bypasses `MarketDataNode` (direct `fetch_quote`).
- `capture_gold_chart` bypasses `VisualCaptureNode`.
- `analyze_gold` always runs the **full** orchestrator. The model cannot
  choose structure-only, news-only, or skip visual capture at runtime.
- Follow-up / supersede / gate report are still separate code paths
  (tools or light-path modes), not one loop that simply doesn't call the
  kernel.
- There is no per-tool Hard Law interceptor. Live-rec blocking lives
  inside `AnalyzeGoldTool.execute` as an ad-hoc `if`.
- There is no output validator. If the model writes "BUY gold at 3300"
  without calling a tool, nothing strips it.

Shortcuts today are **pre-classified modes** (fast-path) or **coarse
tool choice** (agent-first). The unified loop makes shortcuts emerge
from **which evidence tools the model calls**, with Hard Law wrapping
the same loop on every turn.

---

## 3. Problem statement

The routing stack is a fake planner:

1. A regex/keyword classifier decides a fixed mode up front.
2. A hardcoded mode → plan map (`TurnMode` × 10) requires new code in
   3–4 files to add or change a behaviour.
3. Two duplicated execution paths independently rebuild locale,
   pipeline construction, artifacts, and gate/decision handling.
4. No runtime reasoning over evidence: every branch is decided before
   any node runs.

Adding "the model is also in agent-first mode" does not fix (2)–(4) for
recommendation turns: `analyze_gold` is still a full-pipeline dump.

---

## 4. Goal

One unified agent turn loop:

- **Single entry.** Operator message + session/conversation state enter
  the existing `AgentLoop` / `AgentRunner`. We do **not** invent a
  second loop. `.agent/design.md` forbids bloating `loop.py`; gold
  behaviour lives in tools, a policy wrapper, and the gold skill.
- **The model chooses evidence via real tool calls.** Evidence Nodes
  (`market_data`, `structure`, `liquidity`, `supply_demand`,
  `multi_timeframe`, `news`, `geometry`, `risk`, `visual_capture`) are
  invoked as tools. Their bodies call the existing `EvidenceNode.execute`
  / `run_evidence_graph` machinery.
- **One execution path** for price questions, full analysis, follow-up,
  chart requests, and gate inquiries. A pure price question does not
  skip a "light" module — the model simply never calls the kernel tool.
- **Hard Law is a policy layer** around that loop (input + per-tool +
  output). The model cannot bypass it. See §6.
- **Trading kernel unchanged.** `recommendations/store.py`,
  `recommendations/state_machine.py`, and `gates/*.py` are out of scope
  for the implementation that follows this design.

---

## 5. Target architecture

```
Operator message + session state
        │
        ▼
┌───────────────────────────────────────────┐
│  INPUT POLICY                             │
│  • XAUUSD-only context                    │
│  • inject live-plan snapshot (existing    │
│    gold_intent_runtime_context)           │
│  • attach empty turn-scoped               │
│    PipelineContext                        │
│  • tool allowlist for this turn           │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│  AgentRunner (existing nanobot loop)      │
│  model ⇄ tool calls until it stops        │
│                                           │
│  Evidence tools  → EvidenceNode / graph   │
│  Session tools   → live rec / manage plan │
│                    / gate report          │
│  Kernel tool     → synthesizer + gates    │
│                    + store (Hard Law)     │
│  Team / spawn    → evidence briefs only   │
│                    depth=1, budget=4      │
│                                           │
│  every call goes through TOOL POLICY      │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│  OUTPUT POLICY                            │
│  • BUY/SELL only if kernel emitted it     │
│  • prices only from evidence / quote JSON │
│  • hide gate ids, feed names, node names  │
│  • single delivery: locale + artifacts    │
│    + channel cards                        │
└───────────────────────────────────────────┘
        │
        ▼
  OutboundMessage (one path, every case)
```

### 5.1 Core formula (revised)

```
Existing nanobot tool-calling loop
    + Evidence Nodes as tools
    + Privileged kernel tool
    + Hard Law policy wrapper
```

Not: regex planner + mode enum + light/full split.

The 2026-09-13 formula ("Dynamic Agentic Planner + Deterministic Trading
Kernel") was the right split of **authority**. The mistake was
implementing the left-hand side as `TurnPlanner`. The left-hand side is
the model. The right-hand side stays code.

### 5.2 Turn-scoped evidence, not a pre-built DAG

Each user turn owns one `PipelineContext` (symbol coerced to `XAUUSD`,
interval from the tool args or default `15m`). Evidence tool calls
**accumulate** on that context.

- Calling `fetch_evidence(nodes=["market_data"])` runs `MarketDataNode`
  via `run_evidence_graph(graph_for_nodes(...))` and writes `ctx.market`.
- A later `fetch_evidence(nodes=["structure","news"])` runs those nodes
  against the **same** context (dependencies already satisfied are not
  re-fetched unless the caller passes `refresh=true`).
- `run_evidence_graph` already aborts the layer walk when
  `market_data` sets `ctx.aborted`. That behaviour is unchanged.

The default full-analysis layer order in `evidence/graph.py` remains the
dependency source of truth. `graph_for_nodes()` already filters that
layering. Tools must not invent a second DAG.

If the model requests `geometry` without `structure`, Policy Guard
either auto-runs the declared `depends_on` chain (logged as an
adjustment) or refuses — that is Open Question **Q2**.

### 5.3 Kernel is a tool, not a mode

`run_trading_kernel` (name TBD) is the **only** tool that may:

1. Call `run_final_decision_synthesizer`.
2. Run the gate chain (today G1–G20 + G7 reprice loop).
3. Call `store_recommendation`.
4. Return a structured recommendation wire that the output policy will
   treat as an authorized BUY/SELL.

It is not a routing mode. The model may call it after gathering
evidence, or not call it at all (price, chart, follow-up, chat).

Policy refuses the kernel when:

- `SYNTHESIS_REQUIRED_NODES` are missing from the turn context
  (unless Q2 says auto-fetch).
- A live recommendation exists for the session and this turn has not
  gone through `manage_trading_plan` / explicit supersede confirmation.
- `run_kernel` equivalent of today's `turn_plan.run_kernel=false`
  situations (gate report, conversation). Those are simply "don't call
  this tool".
- Kill switch is on (orchestrator already returns wait).

Gates still **never flip** direction. They veto → `wait` or apply
`confidence_delta`. Repeat-error refusal in the orchestrator stays
inside the kernel tool, not in the model.

### 5.4 Follow-up, supersede, chart, gate report are tools — not modes

| Today's `TurnMode` | Unified-loop behaviour |
|--------------------|------------------------|
| `market_data_only` | Model calls `fetch_evidence(["market_data"])` or `get_gold_quote`; replies from JSON. |
| `chart_capture` | Model calls `capture_gold_chart` (backed by `VisualCaptureNode` / capture service). |
| `recommendation_followup` | Model calls `get_live_recommendation` (grades via existing `grade_live_recommendation`). |
| `recommendation_supersede` | Model calls `manage_trading_plan` then, after operator confirm, `run_trading_kernel`. Kernel still refuses a second live rec. |
| `gate_report` | Model calls `get_gate_report` (existing `build_gate_report_result`). `run_kernel=false` is implied: the tool never touches the synthesizer. |
| `full_analysis` | Model gathers required nodes (or a bundled kernel helper — **Q1**) then `run_trading_kernel`. |
| `team_swarm` | Model calls `run_trading_team`; roles produce **evidence briefs** only; kernel still synthesizes. |
| `reevaluation` | Kernel with `reevaluate=true` (same-side only; existing rule). |
| `specialist` / `conversation` | No kernel call. Ordinary chat. |
| `gate_report` with no live plan | Tool returns "no live plan"; no synthesizer. |

No new `TurnMode` is added. The enum is retired from the hot path.

### 5.5 Single delivery path

Light and full paths both do locale + artifacts + `OUTBOUND_META_AGENT_UI`
today, twice. After this redesign, **one** helper (extracted from
`turn_executor` / `orchestrator` / `tool_delivery.py`, name TBD) owns:

- `locale_from_text`
- artifact application (`apply_result_artifacts` / price artifacts /
  plan-status artifacts)
- stage publishing (`TradingStagePublisher`) when `present_ui=true`
- channel-specific recommendation cards (Telegram HTML, WhatsApp text)
- user-facing opacity (i18n labels; never G1-G20 ids, never OANDA, never
  node wire names)

Every tool returns JSON to the model. The helper runs when a tool sets
`present_ui=true` **or** when output policy attaches artifacts to the
final assistant message. Agent-first's "JSON by default, UI opt-in"
rule stays (`should_publish_trading_ui`).

---

## 6. Hard Law (frozen — never delegated to the model)

These rules are enforced in **code**, not prompt text. Prompts may
repeat them for the model's benefit; they are not the control plane.

| Rule | How it is enforced today | How it attaches to the unified loop |
|------|--------------------------|-------------------------------------|
| **Symbol: XAUUSD only** | `gold.require_gold` / `GoldOnlyError`; quote tool catches it | Input policy coerces symbol. Every evidence/kernel tool calls `require_gold`. Non-gold questions get an honest refusal, not a fabricated other-pair analysis. |
| **Recommendations only — no broker orders** | Analysis tools never place orders. `mt5_*` is propose → operator confirm (playbook 182 excluded). | Unchanged. Kernel tool cannot call `mt5_confirm_order`. Output policy rejects assistant text that claims an order was filled. HITL MT5 tools remain a **separate** surface (Open Question **Q12**). |
| **Decision authority** | Only `run_final_decision_synthesizer` issues buy/sell. `apply_model_decision` coerces the synth JSON. | Only `run_trading_kernel` may call the synthesizer. Evidence tools, teams, and spawn return structured evidence / briefs with **no** `decision` field. |
| **Gates** | Chain may veto or `confidence_delta`; orchestrator maps veto → `wait`. Never assigns the opposite side. | Same code, inside the kernel tool. Policy forbids any other tool from mutating `decision.recommendation.action`. |
| **One live recommendation per conversation** | `store_recommendation` returns `""` if a live row exists. Agent-first `analyze_gold` errors unless `force_new_plan`. Fast-path uses regex `wants_explicit_new_analysis`. | Kernel tool + store (unchanged) are the backstop. Input policy injects live-plan context. `force_new_plan` / `manage_trading_plan` remain explicit. Regex is **not** the enforcement; it may remain as a UX hint. |
| **Price integrity** | Skill + quote JSON `instruction`; no code strips invented prices | Output policy: numeric prices in the user-facing reply must appear in this turn's evidence/quote/live-plan JSON (exact match or documented rounding — **Q13**). If data is missing, the reply must say so, not guess. |
| **Spawn depth `max_depth=1`** | `TurnBudget.max_spawn_depth` clamped in Policy Guard. Real depth control is `SpawnTool._scopes = {"core"}` so subagents do not receive `spawn`. | Keep scope restriction. Policy also refuses `spawn` if `RequestContext` already marks the caller as a subagent. Budget clamp stays at 4. |
| **Spawn budget** | `agents.defaults.max_concurrent_subagents` (default 4); Policy Guard clamps card sums | Unchanged. Policy clamps requested spawn, logs `capability_spawn_budget_capped`-style adjustments. |
| **User-facing opacity** | Skill + `i18n` labels | Output policy scrubs wire ids if the model leaks them. |

### 6.1 Policy wrapper shape

Evolve `policy_guard.py` from `validate_turn_plan(TurnPlan)` to three
hooks. `TurnPlan` validation remains **only** as long as the legacy
fast-path is still compiled in (rollback). New hooks:

```
validate_turn_input(message, session) -> TurnSession
    # attach PipelineContext, live rec, allowlist, budgets

validate_tool_call(turn, tool_name, args) -> ToolCallPermit | PolicyViolation
    # unknown node, symbol, kernel preconditions, spawn depth,
    # live-rec lock, subagent cannot call kernel

validate_turn_output(turn, assistant_text, kernel_result) -> OutboundMessage
    # BUY/SELL authorization, price integrity, opacity, delivery
```

`PolicyViolation` stays a hard failure (tool returns an error JSON the
model can recover from; it does not crash the gateway). Kernel
violations must not leak a half-written recommendation into the store —
`store_recommendation` already no-ops incomplete / duplicate rows;
keep that.

### 6.2 What the model must be unable to do

Even with a jailbroken prompt or a confused tool sequence:

1. Emit BUY/SELL that did not come from `run_final_decision_synthesizer`
   this turn.
2. Flip a synthesizer side via a gate, team brief, or follow-up grade.
3. Store a second live recommendation while one is active.
4. Fetch or analyze a non-gold symbol.
5. Confirm/send a broker order from the analysis kernel.
6. Spawn a subagent that can spawn again, or that can call the kernel.
7. Quote a price that does not exist in this turn's evidence JSON.

Items 1 and 7 are **new** code relative to today. Items 2–6 already
exist in pieces and must be wired into the unified interceptor so they
cannot be skipped by "just talking".

---

## 7. Tool surface (proposed)

### 7.1 Evidence — `fetch_evidence`

One tool, not nine, so the model can request a subgraph in a single
round trip (parallel layer execution is already in `run_evidence_graph`).

```
fetch_evidence(
  nodes: list[str],          # subset of NODE_REGISTRY
  interval?: str,            # default 15m
  refresh?: bool,            # default false; re-run even if ctx has the node
  present_ui?: bool          # stage streaming; default false
) -> JSON evidence slices + missing/aborted reasons
```

Implementation: `graph_for_nodes(set(nodes) ∪ depends_on)` then
`run_evidence_graph(turn.pipeline, graph)`. Returns only JSON derived
from `PipelineContext` fields. Never includes `decision`, `action`, or
BUY/SELL.

`get_gold_quote` can remain as a thin alias of
`fetch_evidence(["market_data"])` plus the existing display-formatting
helpers, or be deleted (**Q5**). Direct `fetch_quote` bypass of the
node is how invented "3300-range" quotes sneak past market-sync checks;
prefer the node.

### 7.2 Session / operator tools (already exist, keep)

| Tool | Change |
|------|--------|
| `get_live_recommendation` | Keep. May optionally refresh mid via `market_data` node instead of raw `fetch_quote`. |
| `manage_trading_plan` | Keep. This is the explicit supersede / archive control plane. |
| `get_gate_report` | **New** (logic already in `recommendations/gate_report.py`). Fast-path `gate_report` mode becomes this tool. |
| `capture_gold_chart` | Keep; route through `VisualCaptureNode` when a turn context exists so the kernel can reuse snapshots. |

### 7.3 Kernel — `run_trading_kernel`

```
run_trading_kernel(
  interval?: str,
  reevaluate?: bool,         # same-side only
  force_new_plan?: bool,     # requires operator-confirmed supersede
  gather_missing?: bool,     # Q2 — auto-run SYNTHESIS_REQUIRED_NODES
  present_ui?: bool
) -> recommendation wire (same shape as today's result_to_wire)
```

Internals are a **lift** of the post-evidence half of
`run_unified_chart_agent` (synthesizer → repeat-error → gates → reprice
→ drawings → store → artifacts). Evidence gathering is **not** inlined
unless `gather_missing` is explicitly allowed.

`analyze_gold` becomes either this tool or a deprecated alias (**Q1**).

### 7.4 Teams and spawn

`run_trading_team` / debate crew stay. They produce `team_briefing`
strings that already flow into the synthesizer as `team_briefing=`.
They must not call `run_trading_kernel` internally in the unified-loop
world — today's `run_swarm` / `run_debate_crew` **do** call
`run_unified_chart_agent` at the end. Cutover needs those runtimes to
return briefs only; the parent loop calls the kernel once. That is a
behaviour-preserving refactor of `teams/runtime.py` and `crew/debate.py`
behind the same flag (**Q11**).

Subagent tool allowlist (Hard Law):

- Allowed: evidence fetch (read-only JSON), web, message (if already in
  scope), role-specific prompts.
- Forbidden: `run_trading_kernel`, `analyze_gold`, `manage_trading_plan`,
  `mt5_confirm_order`, `spawn`.

### 7.5 Capability cards

Phase L cards (`price_quote`, `chart_snapshot`, `macro_scan`,
`structure_review`, `committee`, `debate`, `gate_report`) are a regex
overlay on `TurnMode`. They are **not** needed as a planner. Options
(**Q9**):

- Retire the catalog from the hot path; fold `required_nodes` /
  `max_subagents` into tool descriptions and Policy Guard constants.
- Keep cards as **documentation / cost hints** the model can read, not
  as something `plan_turn()` attaches.

---

## 8. What is replaced vs frozen

| Module | Fate |
|--------|------|
| `intent_router.py` | Retired from the hot path. May linger as a **shadow comparator** (log "what regex would have said") then delete after cutover. |
| `turn_planner.py` | Retired from the hot path. `TurnPlan` / `TurnMode` remain only for legacy fast-path + tests until rollback window ends. |
| `node_planner.py` | Delete with the planner; "quick analysis" is the model omitting `visual_capture`. |
| `capabilities/planner.py` | Delete from hot path (**Q9**). |
| `turn_executor.py` | Delete after delivery helper extraction. Light paths become tool implementations. |
| `fast_path.py` | Keep compiled behind `LONORA_UNIFIED_LOOP=off` (and `LONORA_AGENT_FIRST=false`) as **rollback**. Remove after the rollback window. |
| `orchestrator.py` | Split: evidence half → evidence tools; kernel half → `run_trading_kernel`. HTTP `/api/trading/analyze` calls the kernel tool's Python function, not a second pipeline. |
| `policy_guard.py` | Evolve as in §6.1. Do not weaken. |
| `evidence/*` | Keep. |
| `gates/*` | Keep. |
| `recommendations/store.py` | Keep. |
| `recommendations/state_machine.py` | Keep. |
| `agents/synthesizer.py` + `apply_model_decision.py` | Keep. |

---

## 9. Migration — no hard cutover

This is a live recommendation system. Implementation that follows this
design **must** land behind a flag, run in shadow, then cut over with
instant rollback.

### 9.1 Flag

Tri-state env, default **off** (production unchanged):

```
LONORA_UNIFIED_LOOP=off|shadow|on
```

| Value | User-visible path | Unified loop | Notes |
|-------|-------------------|--------------|-------|
| `off` (default) | Today's code: `LONORA_AGENT_FIRST` / fast-path as now | Not run | Rollback target. |
| `shadow` | Today's code | Run in parallel; **discard** its outbound | Log comparison. Never store a second recommendation from the shadow run. |
| `on` | Unified loop | Only path for chat turns | Fast-path not entered. HTTP analyze uses kernel function. |

Do **not** default this on. `LONORA_PLANNER_SHADOW` (expand subsets to
the full graph) is a different flag and becomes a no-op once unified
loop is `on` (there is no subset plan to expand).

`LONORA_AGENT_FIRST` relationship:

- Unified `off` + agent-first `true` = current production.
- Unified `shadow` implies the current production path still serves
  users; agent-first stays as it is.
- Unified `on` **implies** agent-first (regex hijack is off). Setting
  `LONORA_AGENT_FIRST=false` while unified is `on` is invalid config
  and must log + refuse to enable unified.

Open Question **Q7**: collapse to one flag vs keep both.

### 9.2 Shadow comparison (what to log)

For every shadowed turn, write one structured log line (and keep it
out of user-facing channels):

```
unified_loop_shadow
  session_key, channel, locale
  old_path: agent_first | fast_path
  old_mode / old_intent / old_nodes          # from plan_turn, even if unused
  old_tools: [...]                           # tools the serving path actually ran
  old_kernel: bool
  old_decision: buy|sell|wait|none
  old_rec_id
  new_tools: [...]
  new_nodes: [...]
  new_kernel: bool
  new_decision: buy|sell|wait|none
  new_would_store: bool                      # must be false in shadow
  divergence: list[str]                      # kernel_mismatch, side_mismatch,
                                             # node_set_mismatch, price_mismatch, …
  latencies_ms: {old, new}
```

**Shadow must never** call `store_recommendation`. Pass `store=False`
into the kernel function (orchestrator already has `store: bool`).

**Dual LLM cost:** a faithful "what the unified loop would have done"
requires a second model conversation. That is expensive and can change
the primary turn's provider rate limits.

Recommended approach (sign-off **Q3**):

1. **Always** (cheap): after the serving path, log `plan_turn()` (regex
   counterfactual) vs actual serving tools. This already explains
   "regex would have said X, agent-first did Y".
2. **Sampled dual-run** (default 10%, configurable
   `LONORA_UNIFIED_LOOP_SHADOW_SAMPLE`): clone the turn with a separate
   tool registry, run AgentRunner with a timeout budget, discard output.
   If the sample errors or times out, log `shadow_error` and move on —
   never block the operator.
3. **Replay harness** in CI: fixture transcripts (price, chart,
   follow-up, full analysis, gate inquiry, supersede, live-rec lock)
   run against both stacks with a fake provider that returns scripted
   tool calls. This is the safety net that does not depend on live LLM
   nondeterminism.

Shadow period: keep `shadow` in production until:

- No `side_mismatch` on sampled dual-runs for a defined window.
- Replay harness green in CI.
- Divergence on `kernel_mismatch` understood (e.g. model skipped
  kernel on a recommendation request — prompt/skill issue, not a
  silent kernel skip).

Then flip `on` per environment (staging first, then production).
Rollback is `LONORA_UNIFIED_LOOP=off` (or unset). No data migration.
Shadow rows were never stored.

### 9.3 Suggested implementation order (after sign-off)

Not in this PR. Listed so the flag work is sequenced:

0. **This design** + Open Questions sign-off.
1. Turn-scoped `PipelineContext` on `RequestContext` + `fetch_evidence`
   tool wrapping existing nodes. Flag off: tool not registered.
2. Policy interceptor (input / tool / output) behind the flag; output
   policy can already wrap agent-first replies for BUY/SELL and prices
   as a dry-run log.
3. Lift kernel half of orchestrator into `run_trading_kernel`;
   `analyze_gold` delegates when flag is on.
4. Unify delivery helper; migrate quote / chart / follow-up / gate
   report tools onto it.
5. Shadow logger + replay fixtures.
6. Team/debate "briefs only, parent calls kernel" under the flag.
7. Staging `on`, then production `on`, then delete fast-path / planner
   after the rollback window.

Each step is a separate PR. Kernel files listed in §2.2 stay untouched
except for call-site moves.

---

## 10. Test coverage gaps (`tests/trading/`)

Existing tests **lock in the architecture we are removing**. They are
valuable as a rollback oracle, not as coverage for the unified loop.

### 10.1 What exists today (routing-centric)

| File | What it actually asserts |
|------|--------------------------|
| `test_intent_router.py` | Regex kind for a handful of EN/AR phrases |
| `test_fast_path.py` | `plan_turn` modes + a few `try_gold_fast_path` hijack/skip cases |
| `test_turn_executor.py` | Light-path price/follow-up with evidence stubs |
| `test_policy_guard.py` | `TurnPlan` node inject, unknown node, spawn clamp, shadow expand-to-full |
| `test_phase_k.py` / `test_phase_l.py` / `test_phase_m.py` | Capability cards, quick-analysis subset, gate_report mode |
| `test_agent_first_mode.py` | **Flag default only** — no loop behaviour |
| `test_trading_tools.py` | `get_gold_quote` unconfigured; `analyze_gold` publishes when `present_ui` |
| `test_tool_delivery.py` | `present_ui` opt-in; live-plan blocks `analyze_gold` |
| `test_evidence_graph.py` | Layer order, abort on market failure, orchestrator parity — **keep and extend** |
| `test_lonora_cognition.py` | Synthesizer / follow-up / store — **keep** |
| `test_gates.py` / `test_risk_gates.py` / `test_plan_alignment.py` | Kernel — **keep, do not rewrite** |
| `test_new_rec_request.py` | Fast-path supersede phrasing |

There is **no** test that:

- Drives `AgentRunner` with a fake provider through a gold turn.
- Asserts BUY/SELL in assistant text is stripped when the kernel did
  not run.
- Asserts fabricated prices are rejected.
- Asserts a subagent cannot call the synthesizer / `analyze_gold`.
- Asserts `max_depth=1` via a nested `spawn` attempt.
- Asserts a shared `PipelineContext` accumulates nodes across tool
  calls in one turn.
- Asserts shadow logs and `store=False` on the shadow kernel.
- Asserts `LONORA_UNIFIED_LOOP=off` is bit-identical to current
  behaviour (flag isolation).

### 10.2 Tests that must exist before `on`

Group A — Hard Law (blockers; sign-off if any assertion is controversial):

1. Kernel tool refused when `SYNTHESIS_REQUIRED_NODES` missing.
2. Kernel tool refused when a live rec exists and `force_new_plan` is
   false; store still has exactly one live row.
3. Gates veto → `wait` with the **same** synthesizer side internally;
   user-visible action is wait. Never `buy`→`sell`.
4. Evidence tool with `symbol=EURUSD` raises / coerces; no EURUSD
   candles in context.
5. Output policy: assistant text "BUY XAUUSD now 2500" with no kernel
   result this turn → not delivered as a recommendation (stripped or
   blocked — **Q6**).
6. Output policy: price `3301.00` not present in quote/evidence JSON →
   rejected or replaced with the feed value / an honest "no quote".
7. Subagent registry does not contain `run_trading_kernel`,
   `analyze_gold`, `spawn`, `mt5_confirm_order`.
8. Nested spawn from a subagent fails closed.
9. Shadow kernel never writes to `recommendations` SQLite.

Group B — loop behaviour:

10. Price question: fake provider calls `fetch_evidence(["market_data"])`
    only; kernel not called; reply contains stub mid.
11. Chart question: `capture_gold_chart` only.
12. Follow-up with live rec: `get_live_recommendation`; kernel not
    called; store unchanged.
13. Gate inquiry: `get_gate_report`; `run_kernel` equivalent false.
14. Fresh analysis: evidence nodes then kernel; store gains one row.
15. `PipelineContext` sharing: structure tool sees market from the
    earlier call in the same turn.
16. Unknown node id → `PolicyViolation` JSON, turn continues.

Group C — flag / rollback:

17. `LONORA_UNIFIED_LOOP=off` → `try_gold_fast_path` / agent-first
    behaviour unchanged (existing tests still pass).
18. `shadow` → serving path outbound equals `off`; extra log emitted;
    no extra store row.
19. Invalid combo `on` + `LONORA_AGENT_FIRST=false` → safe fallback to
    `off` or hard config error (pick in **Q7**).

Group D — keep as-is during migration:

- All `gates/`, `state_machine`, `store`, synthesizer cognition tests.
- `test_evidence_graph.py` (add subgraph + dependency cases).

Do not rewrite Group D to "use the new loop" in the first
implementation PRs. Kernel tests should keep calling kernel functions
directly.

### 10.3 Legacy tests after cutover

Once `on` is default and the rollback window ends, convert
`test_intent_router.py` / `test_fast_path.py` / `test_turn_executor.py`
into characterization fixtures or delete them with the modules. Until
then they guard the off-path.

---

## 11. Relationship to earlier phases (H–M)

| Phase | What actually shipped | Unified-loop stance |
|-------|----------------------|---------------------|
| H Evidence Nodes | Real graph executor | **Keep** — this is the tool backend. |
| I TurnPlan + Policy Guard | Static plan + shadow-expand-to-full | Policy Guard **evolves**; `TurnPlan` becomes legacy. Shadow meaning changes (see §9). |
| J Light executor | Duplicated delivery | **Replace** with tools + one delivery helper. |
| K Full-analysis subsets | Regex "quick" drops visual | **Replace** — model omits the node. |
| L Capability cards | Regex overlay | **Q9**. |
| M State machine + observability | Real FSM + structured logs | **Keep**. Add unified-loop shadow logs to `observability.py`. |

Agent-first (`LONORA_AGENT_FIRST`) is a parallel track that already
skipped regex hijack. Unified loop is the next step: evidence
granularity + Hard Law as a real wrapper, not a `TurnPlan` linter.

---

## 12. Open Questions — sign-off required before implementation

Items marked **Hard Law** change an enforcement point. Do not assume a
default.

### Q1. Bundled `analyze_gold` vs granular nodes only  **Hard Law-adjacent**

Should the model still have a single tool that gathers
`SYNTHESIS_REQUIRED_NODES` and runs the kernel in one call?

- **A (recommended default to discuss):** Keep a privileged
  `run_trading_kernel(gather_missing=true)` / `analyze_gold` alias for
  recommendation turns (1 round trip, current latency). Granular
  `fetch_evidence` is how shortcuts emerge. Kernel still refuses if
  store/live-rec/kill-switch say so.
- **B:** No bundled gather. Model must call `fetch_evidence` then
  `run_trading_kernel`. More round trips; more failure modes if the
  model forgets `risk` or `news`.

### Q2. Missing synthesis nodes: inject or refuse?  **Hard Law**

Today `_normalize_nodes` **injects** `SYNTHESIS_REQUIRED_NODES` and
logs `injected_required_nodes`.

- **A:** Keep inject inside the kernel tool (deterministic, matches
  today). Logged adjustment.
- **B:** Hard refuse; model must fetch. Purer "model decides", worse
  reliability.
- **C:** Inject only when `gather_missing=true` (ties to Q1).

### Q3. Shadow dual-run sampling

Approve the §9.2 mix (always log regex counterfactual; sample 10%
second LLM run; CI replay harness)? Different sample rate? Staging-only
dual-run?

### Q4. Gate ids in Hard Law copy  **Hard Law**

The 2026-09-13 Hard Law table says **G1–G7**. `build_gates.py` now
defines **G1–G20** (spread, cooldown, max positions, drawdown, session
lock, …). This redesign will **not** drop G8–G20.

Confirm: "gates may block or adjust confidence, never flip direction"
applies to the **entire live chain**, not a G1–G7 subset.

### Q5. `get_gold_quote` vs `market_data` node only

Keep the dedicated quote tool (familiar to the skill / operator) as a
wrapper around `MarketDataNode`, or delete it and teach the skill
`fetch_evidence(["market_data"])` only?

### Q6. Output validator aggressiveness  **Hard Law**

When the model writes BUY/SELL without a kernel result this turn:

- **A:** Strip / rewrite the sentence; still send a chat reply.
- **B:** Block the outbound message; send a fixed i18n apology.
- **C:** Only block **structured** recommendation artifacts / store
  writes; allow conversational "I'd be a buyer if …" hedging.

C is weaker. A is the recommended discussion default.

### Q7. Flag taxonomy

Keep `LONORA_UNIFIED_LOOP` + `LONORA_AGENT_FIRST` +
`LONORA_PLANNER_SHADOW`, or collapse?

Recommended: tri-state unified flag (§9.1); agent-first remains until
unified is `on`; planner-shadow ignored when unified is `on`.

Invalid combo `on` + agent-first `false`: **error and fall back to
`off`**, or refuse to start the gateway?

### Q8. Rollback window after `on`

How long must `fast_path.py` / `turn_planner.py` remain loadable? A
defined number of production days/weeks is a product call; this design
only requires that `off` restore today's behaviour until you say
otherwise.

### Q9. Capability cards

Retire from the hot path, or keep as model-readable cost hints?

### Q10. HTTP `/api/trading/analyze` and supersede buttons

These skip `AgentLoop` today. Under unified `on`:

- **A:** Call the same Python kernel function (no LLM). Buttons stay
  deterministic.
- **B:** Synthesize a fake operator message and run the full unified
  loop (nondeterministic, slower).

**A** is the recommended default so HITL supersede approve cannot
"forget" to analyze.

### Q11. Debate / swarm finals  **Hard Law-adjacent**

Today `run_swarm` / `run_debate_crew` call `run_unified_chart_agent`
themselves (a second synthesizer). Unified loop wants **one** kernel
call in the parent.

Confirm: team tools return briefs only; parent (or HTTP analyze) calls
the kernel once. Teams never emit BUY/SELL.

### Q12. MT5 HITL vs "recommendations only"  **Hard Law**

The frozen table says recommendations only — no broker orders. The repo
also ships `mt5_propose_order` / `mt5_confirm_order` with mandatory
HITL.

Confirm this redesign **does not** remove HITL execution, and **does
not** let the kernel or evidence tools confirm orders. Analysis and
execution remain separate tool surfaces.

### Q13. Price match rule  **Hard Law**

Exact string match against `display.mid` / evidence JSON, or allow
rounding to 2 decimal places? Today's skill demands verbatim
`display.mid` (e.g. `4342.60`, no thousands commas).

### Q14. Spawn depth enforcement location  **Hard Law**

Today `max_depth=1` is mostly "subagents don't get the spawn tool"
(`_scopes`). `TurnBudget.max_spawn_depth` is only a planner field.

Confirm we treat **tool scope + interceptor** as the law, and do not
rely on `TurnPlan` after cutover. Also confirm default concurrent cap
stays **4**.

### Q15. Skill line "You may not answer WAIT"

`skills/gold-trading/SKILL.md` tells the conversational agent it may
not answer WAIT, while the kernel/gates routinely produce `wait`. This
redesign will **not** change that doctrine unless you say so. Confirm
leave-as-is.

---

## 13. References

- This proposal replaces the Hybrid Runtime narrative that previously
  occupied this file.
- Product roadmap: `docs/designs/gold-trading-roadmap.md`
- Original agent design: `docs/designs/gold-trading-agent.md`
- Architecture constraints: `.agent/design.md`
- Evidence graph: `nanobot/trading/evidence/`
- Current (legacy) planner: `nanobot/trading/turn_planner.py`
- Current Policy Guard: `nanobot/trading/policy_guard.py`
- Current light path: `nanobot/trading/turn_executor.py`
- Current full path: `nanobot/trading/orchestrator.py`
- Current agent-first tools: `nanobot/agent/tools/trading_chart.py`
- Agent-first skip of fast-path: `nanobot/agent/loop.py`
  (`_dispatch_gold_fast_path`)
- Kernel store: `nanobot/trading/recommendations/store.py`
- Kernel FSM: `nanobot/trading/recommendations/state_machine.py`
- Gates: `nanobot/trading/gates/`
- Gold skill: `nanobot/skills/gold-trading/SKILL.md`
