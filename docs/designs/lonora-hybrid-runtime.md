# Lonora Hybrid Runtime — Design & Implementation Plan

> Saved: 2026-09-13  
> Status: **APPROVED** — Phase H in progress  
> Branch: `cursor/lonora-hybrid-runtime-7a52`  
> Supersedes: ad-hoc discussion notes (GPT + Claude review, ~85–90% consensus)

---

## Problem Statement

Nanobot gold mode today is a **structured recommendation system**: a fixed pipeline
(`market_data → specialists → synthesizer → G1–G7 → store`) with optional YAML swarm
teams. It is honest and governable, but **inflexible** compared to Cursor / Claude Code
orchestrators that dynamically choose depth, tools, and deliverables per turn.

The hybrid runtime keeps the **deterministic trading kernel** (synthesizer ownership,
gates, one live recommendation, XAUUSD only) while giving Lonora a **dynamic planner**
that decides *which* evidence nodes to run, *how many* subagents to spawn, and *which*
artifacts to emit — within hard budgets.

---

## Core Formula

```
Dynamic Agentic Planner  +  Deterministic Trading Kernel
```

### Runtime flow (target)

```
User message
    ↓
Lonora (single conversational agent)
    ↓
TurnPlanner          — intent + mode + tool flags (exists today, will expand)
    ↓
Policy Guard         — Phase I: validate plan against Hard Law before execution
    ↓
Dynamic DAG Executor — Phase J–K: run selected Evidence Nodes
    ↓
Evidence Graph       — structured node outputs (Phase H)
    ↓
Synthesizer          — sole BUY/SELL authority (unchanged)
    ↓
Gates G1–G7          — block / confidence delta, never flip side (unchanged)
    ↓
Recommendation Store — one live rec per conversation (unchanged)
    ↓
Artifacts + Response — agent-chosen deliverables (Phase G done)
```

---

## Hard Law (frozen — never delegated to planner or subagents)

| Rule | Detail |
|------|--------|
| **Symbol** | XAUUSD only |
| **Execution** | Recommendations only — no broker orders |
| **Decision authority** | `run_final_decision_synthesizer` alone issues BUY/SELL |
| **Gates** | G1–G7 may veto or adjust confidence; they **never flip** direction |
| **Live recommendation** | One per conversation unless operator explicitly requests new analysis |
| **Price integrity** | No fabricated prices — frozen evidence JSON only |
| **Spawn depth** | `max_depth = 1` — subagents cannot call `spawn` |
| **Spawn budget** | `agents.defaults.max_concurrent_subagents` (default 4) |
| **User-facing opacity** | Hide internal ids (G1–G7, OANDA, node wire names) |

---

## Dynamic surface (planner decides — within Policy Guard)

| Decision | Today | Target |
|----------|-------|--------|
| Which pipeline stages run | Always full fleet | Planner selects Evidence Nodes |
| Subagent count | 0 or full YAML preset | 0–N roles within token/latency budget |
| Artifacts | LLM picks from catalog (Phase G) | Same + planner can skip synthesis path |
| Response verbosity | Mostly fixed | Short / detailed per intent |
| Team mode | Explicit `team_swarm` intent | Planner may invoke committee when warranted |

Subagents and swarm roles produce **structured evidence** (Evidence Nodes or briefs).
They never call `analyze_gold`, never issue BUY/SELL, and never bypass gates.

---

## Evidence Node model (Phase H)

An **Evidence Node** is the atomic unit of the analysis DAG:

```python
EvidenceNode:
    id: str                    # e.g. "structure", "visual_capture"
    stage: str | None          # stage_events key; None = silent (e.g. geometry)
    depends_on: tuple[str, ...]
    async execute(ctx) -> None # mutates PipelineContext
```

**PipelineContext** holds all intermediate results (`market`, `structure`, `liquidity`,
`mtf`, `news`, `geometry`, `risk`, `visual`, `snapshots`, …).

**EvidenceGraph** defines layers — nodes within a layer run concurrently; layers run
serially. Phase H ships the **default full-analysis graph** identical to today's
`run_unified_chart_agent` ordering (no visible behavior change).

### Default graph layers (Phase H)

| Layer | Nodes | Notes |
|-------|-------|-------|
| 1 | `market_data` | Abort pipeline on sync failure |
| 2 | `structure`, `liquidity`, `supply_demand`, `multi_timeframe` | Parallel fleet |
| 3 | `news` | Macro / calendar |
| 4 | `geometry` | Silent — derived from structure |
| 5 | `risk` | Candidates for synthesizer |
| 6 | `visual_capture` | Stage key `research` |

**Not Evidence Nodes (trading kernel):** synthesizer, gates, reprice loop, drawing,
recommendation store. These stay in `orchestrator.py` after the evidence phase.

---

## Capability Cards (Phase L — planned)

Planner-readable cards describing optional capabilities:

| Card | Triggers | Subagent? |
|------|----------|-----------|
| `price_quote` | Price / spread questions | No |
| `chart_snapshot` | Chart image intent | No |
| `macro_scan` | News-heavy questions | Optional 1 role |
| `structure_review` | Level / trend questions | Optional 1 role |
| `committee` | Complex recommendation | 3–5 YAML roles |
| `debate` | Bull/bear conflict | 2–3 roles |
| `gate_report` | "Why blocked?" follow-up | No — reads stored gate chain |

Each card declares: `cost_estimate`, `required_nodes`, `max_subagents`, `output_schema`.

---

## Implementation phases

### Phase H — Evidence Nodes ✅ *in progress*

- [x] Design doc (this file)
- [ ] `nanobot/trading/evidence/` package
- [ ] `EvidenceNode` interface + registry
- [ ] Default graph executor (same order as current orchestrator)
- [ ] Refactor `orchestrator.py` evidence gathering through executor
- [ ] Tests: registry, layer order, market failure short-circuit, orchestrator parity

**Success:** `pytest tests/trading/ -q` green; no user-visible behavior change.

### Phase I — TurnPlan + Policy Guard ✅ *implemented*

- [x] Extend `TurnPlan` with `nodes: tuple[str, ...]` and `budget: TurnBudget`
- [x] `validate_turn_plan(plan) -> ValidatedPlan` + `PolicyViolation` on hard failures
- [x] Shadow mode (`LONORA_PLANNER_SHADOW`, default `true`): logs planned vs executed nodes
- [x] Orchestrator + fast_path pass `turn_plan` into evidence graph resolution
- [ ] Metrics export (structured log only today; Phase M)

### Phase J — Dynamic Executor (light paths)

Planner fully controls:

- `market_data_only` (price quote)
- `chart_capture` (screenshot)
- `recommendation_followup` (grade live plan)

No change to full-analysis kernel yet.

### Phase K — Dynamic Executor (full analysis)

Planner selects Evidence Node subset for full recommendations:

- Example: "what are the gates?" → `gate_report` artifact only, no re-synthesis
- Example: fresh analysis → full default graph
- Fallback: if planner omits required node for synthesis, Policy Guard injects it

### Phase L — Capability Cards + dynamic committee

- Card catalog in `nanobot/trading/capabilities/`
- Planner maps intent → cards → nodes + optional subagent roles
- Hard budgets: `max_agents`, `max_tokens`, `max_latency_ms`

### Phase M — Recommendation state machine + observability

- Explicit FSM: `live → in_trade → tp1 → invalidated → closed`
- Dedup outcome alerts across price oscillation
- Structured logs: planner decisions, node timings, gate outcomes

---

## Relationship to existing subsystems

| Subsystem | Role in hybrid runtime |
|-----------|------------------------|
| `turn_planner.py` | Becomes planner front-end (Phase I+) |
| `spawn` / `SubagentManager` | Delegation with depth=1; planner budgets |
| `run_trading_team` | Committee card preset (Phase L) |
| `analyze_gold` / orchestrator | Kernel entry; evidence phase via graph executor |
| `cards/artifacts.py` | Deliverables layer (done — Phase G) |
| `trading-proactive` skill | Proactive comms; separate from runtime DAG |

---

## Consensus trace (GPT + Claude review)

| Topic | Agreement |
|-------|-----------|
| Planner dynamic + kernel static | ✅ Both |
| Keep synthesizer + gates as law | ✅ Both |
| Gradual rollout with shadow mode | ✅ Both |
| Evidence as structured nodes, not free text | ✅ Both |
| Replace fixed pipeline immediately | ❌ Neither — migrate in phases |
| Unbounded subagent spawning | ❌ Neither — hard budgets |

---

## References

- Product roadmap: `docs/designs/gold-trading-roadmap.md`
- Original agent design: `docs/designs/gold-trading-agent.md`
- Turn planner: `nanobot/trading/turn_planner.py`
- Orchestrator: `nanobot/trading/orchestrator.py`
- Evidence snapshot (synthesizer input): `nanobot/trading/agents/evidence.py`
- Spawn tool: `nanobot/agent/tools/spawn.py`
- Team presets: `nanobot/trading/teams/presets/*.yaml`
