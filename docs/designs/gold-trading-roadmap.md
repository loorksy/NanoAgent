# Gold Trading Agent — Roadmap & Product Decisions

> Saved: 2026-09-13 (after Phases A–E on branch `cursor/trading-agent-phase-a-7a52`, PR #16)

This document records **honest product assessment**, **completed work**, and **next directions** — including a user decision that trading output should be **Artifacts**, not fixed static cards.

---

## Completed (Phases A–E)

| Phase | Focus |
|-------|--------|
| **A** | Product honesty: G5 backtest removed, G2/G3 strengthened, honest news macro, real AgentCards UI |
| **B** | Real team subagents (debate/swarm via `run_team_role`) |
| **C** | WebUI chart capture bridge, G4 visual state, outcome tracking + Performance UI |
| **D** | Outcome transition alerts (Telegram/WhatsApp cron), briefing live status, chart capture polish |
| **E** | Telegram chart photo with recommendation caption, WhatsApp Arabic stage checklist, WebUI outcome banners, Inbox filters + paper labels, mobile sheet sync |

**Tests:** `python3 -m pytest tests/trading/ -q` → 97 passed (at time of save).

**Constraints (unchanged):** XAUUSD only, recommendations only (no broker execution), gates always run.

---

## Product honesty — chart images

### What works today

- During **full analysis** from **WebUI** (with TradingView sidecar open), the backend may request `trading_chart_capture`, snapshots feed the synthesizer and G4, and **Telegram** may receive a **photo + HTML recommendation card** when snapshots exist.
- Outcome alerts (`in_trade`, `tp1`, `invalidated`) fire on status transitions (cron + API).

### What does **not** work yet

If the user asks only: **«أرسل لي صورة الشارت»** / **«screenshot the chart»**:

- There is **no dedicated tool** (`capture_gold_chart`, `send_chart_screenshot`, etc.).
- The gold skill does **not** instruct the agent to return a chart image on demand.
- The LLM will often still answer like before: TradingView link, illustrative drawing, or «analysis doesn't return images» — because **chart capture is wired into the analysis pipeline**, not exposed as a **user-facing capability**.

### Gap vs a general-purpose agent (e.g. Claude Agent)

Nanobot gold mode today is a **structured recommendation system** (market data → specialists → synthesizer → G1–G7 → store), not an open-ended trading copilot that satisfies every trading-related intent.

Current tools: `get_gold_quote`, `analyze_gold`, `run_trading_team`.

Missing for «any user idea»: standalone chart export, on-demand reports, portfolio views, custom comparisons, artifact bundles, etc.

---

## Phase F — Chart image on demand (implemented)

**Goal:** When the user asks for a chart image, the agent can answer **yes** with a real screenshot — not a workaround.

| Item | Description |
|------|-------------|
| **Tool** | `capture_gold_chart(interval?, timeframes?)` — open chart (WebUI), capture, return artifact path or send via `message` media |
| **Intent** | Route `chart_image` / Arabic phrases («صورة الشارت», «سكرين شوت», …) with high confidence |
| **Skill** | Update `gold-trading/SKILL.md`: never offer only a TradingView link when capture is available |
| **Channels** | Telegram/WhatsApp: `send_photo` with captured frame even without full recommendation |
| **WebUI** | Show image artifact inline in thread (reuse `nanobot/utils/artifacts.py` + message `media`) |

**Success:** User message «أرسل صورة شارت الذهب 15m» → agent calls tool → user receives image in chat (and optionally Telegram).

**Implemented:** `capture_gold_chart` tool, `chart_image` intent + `chart_capture` turn mode, fast-path on WebUI, `capture_service.py`, session-bound bridge (Phase H security).

---

## Phase G — Artifacts instead of static cards (implemented)

### Problem

Today, `nanobot/trading/cards/derive.py` builds a **fixed ordered list** of card kinds (`decision`, `plan_levels`, `gate_checklist`, `visual_review`, …). WebUI renders them via static React components in `AgentCards.tsx`.

This is **product-static**: every analysis looks the same, regardless of what the user asked or what matters for *this* turn.

### Vision

Trading output should behave like **Artifacts** in a capable agent (Composer / Claude):

- The agent **decides which artifacts to emit** based on intent, evidence, and channel.
- Artifacts are **inspectable deliverables** (image, table, checklist, timeline, chart overlay spec, PDF summary) — not a fixed template.
- The agent knows **when** an artifact helps (e.g. user asked for levels → level table artifact; asked for proof → gate evidence artifact; asked for picture → chart image artifact).

### Examples of artifact kinds (non-exhaustive)

| Artifact | When to use |
|----------|-------------|
| `chart_snapshot` | User wants to *see* price action; visual confirmation |
| `level_map` | Entry / SL / TP discussion; plan review |
| `gate_report` | User questions why blocked or confidence changed |
| `outcome_timeline` | Follow-up on open recommendation |
| `team_briefing` | Debate/swarm mode; show bull/bear/risk summaries |
| `macro_dashboard` | News/macro-heavy questions |
| `paper_ledger_entry` | After approve/reject |

### Implemented

1. **`emit_trading_artifacts()`** in `nanobot/trading/cards/artifacts.py` — 1–4 artifacts per turn; **LLM picks** via synthesizer `artifactsRequested`, with deterministic fallback when empty/invalid. **Operator-intent inference** for price (`price_quote`) and follow-up (`plan_status`, `level_map`, `tracked_plan`) when synthesizer is not called.
2. **Wire:** `artifacts` on `result_to_wire` + `trading_artifacts` agent_ui kind.
3. **WebUI:** `ArtifactRenderer.tsx` (preferred over full `AgentCards` deck when artifacts present).
4. **`cards`** kept for backward compatibility; artifacts are primary.
5. **Chart snapshot** artifact + Telegram photo via `capture_service` / existing card photo path.

### Principle

> **Less fixed UI, more agent-chosen deliverables** — same as a strong general agent: structure when needed (gates, storage), flexibility when the user’s question demands it.

---

## Phase H (user decision) — Intelligent proactive communication

### Problem

Default system cron jobs (`gold_scan` every 30m, `gold_news` every 60m, `gold_rec_followup` every 15m) pushed repetitive Telegram messages (`Gold scanner: Bot note…`, duplicate live-plan reminders) without user consent.

### Vision

- **No default spam bots** — background gold crons are **opt-in** (`gateway.tradingCron.enabled`, default `false`).
- The **agent** decides when to speak using the `trading-proactive` skill: notification gate, market-closed honesty, user-requested watches via `cron` / `HEARTBEAT.md`.
- Operator requests are **open-ended** — not a fixed menu. The agent uses memory (`USER.md`, `MEMORY.md`, session history) to fulfill bespoke watches the docs never listed; examples in the skill are illustrations only.
- Unusual operator requests (e.g. «خبرني لو صار خبر فجأة وأوقف التداول») → agent creates a timed or recurring task, confirms schedule, and alerts only on material change.

### Implemented (docs + config)

- Skill: `nanobot/skills/trading-proactive/SKILL.md`
- Config: `GatewayConfig.trading_cron.enabled` (default `false`)
- `register_trading_cron_jobs(..., enabled=...)` removes jobs when disabled

### Still planned

- Agent-initiated artifact bundles instead of plain text spam (ties to Phase G)

**Done (Phase M):** Outcome-alert dedup across `waiting ↔ in_trade` oscillation — see `nanobot/trading/recommendations/state_machine.py`.

---

## Open questions

1. Should **every** `analyze_gold` still emit a minimal `decision` artifact, or can the agent return *only* a chart image if that was the ask?
2. Artifact authorship: deterministic code only, or LLM picks from an allowed catalog?
3. Backward compatibility: keep `cards` in wire format during migration?

---

## References

- Design spec: `docs/designs/gold-trading-agent.md`
- Implementation audit: `docs/implementation/gold-agent-system-plan.md`
- Card derivation (current): `nanobot/trading/cards/derive.py`
- Artifact storage: `nanobot/utils/artifacts.py`
- Chart capture bridge: `nanobot/trading/chart_capture.py`, `nanobot/trading/chart_photo.py`
