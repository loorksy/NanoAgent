# Gold Agent (AiChart-style) — Implementation Plan

> Derived from **system files** (`mokli/`, `mokli/`, `tests/trading/`), not design docs.

## Current state (code audit)

| Layer | File(s) | Gap |
|-------|---------|-----|
| Agent tools | `mokli/agent/tools/loader.py` scans 26 tools | 23 are general-purpose (shell, filesystem, …) |
| Skills | `mokli/skills/*` (12 dirs) | Only `gold-trading/` is trading-specific |
| Channels | `mokli/channels/*` (17 packages) | Only `websocket`, `telegram`, `whatsapp` needed |
| Intent | `mokli/trading/intent_router.py`, `turn_planner.py` | **Never called** from `mokli/agent/loop.py` |
| Mokli shell | `mokli/src/App.tsx` `ShellView` | `apps/skills/automations/channels` + no `performance` |
| Chart UX | `TradingChartSidecar.tsx`, `#/chart` | Desktop sidecar OK; **no mobile bottom sheet** |
| Telegram | `trading_progress.py` wired; `trading_cards.py` | Cards **orphaned** |
| WhatsApp | `mokli/channels/whatsapp/` | **Zero** trading UX |
| Performance | — | **Missing** (only `TradingStatusBar` in chart panel) |

## Target product shell (AiChart parity)

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar: Chat | Performance | Recommendations | Briefing│
│          Settings (models, channels, memory, runtime)   │
├──────────────────────────┬──────────────────────────────┤
│ Chat (primary)           │ Chart sidecar (desktop ≥768) │
│                          │ Bottom sheet (mobile <768)   │
└──────────────────────────┴──────────────────────────────┘
```

Routes: `#/chat/…`, `#/performance`, `#/recommendations`, `#/briefing`, `#/chart`, `#/settings`

## Phase 1 — DELETE (not disable)

### Tools — remove files

```
mokli/agent/tools/shell.py
mokli/agent/tools/exec_session.py
mokli/agent/tools/filesystem.py
mokli/agent/tools/search.py
mokli/agent/tools/apply_patch.py
mokli/agent/tools/cli_apps.py
mokli/agent/tools/image_generation.py
mokli/agent/tools/self.py
```

### Tools — keep (gold agent allowlist in `loader.py`)

| Module | Tools |
|--------|-------|
| `trading_chart.py` | `get_gold_quote`, `analyze_gold` |
| `trading_team.py` | `run_trading_team` |
| `web.py` | `web_search`, `web_fetch` |
| `message.py` | `message` |
| `spawn.py` | `spawn` |
| `cron.py` | `cron` |
| `long_task.py` | `create_goal`, `update_goal` |
| `sessions.py` | `search_sessions`, `read_session` |
| `session_messages.py` | `list_sessions`, `send_session_message` |

### Skills — remove dirs

`github`, `weather`, `tmux`, `clawhub`, `skill-creator`, `update-setup`, `summarize`, `image-generation`, `my`

Keep: `gold-trading/`, `memory/`, `cron/`

### Channels — remove dirs

All except `websocket/`, `telegram/`, `whatsapp/`

## Phase 2 — Intent routing

1. Add `mokli/trading/gold_intent_context.py` — `plan_turn()` → `RuntimeContextBlock`
2. Register in `AgentLoop.__init__` via `register_runtime_context_provider`
3. Skill `gold-trading/SKILL.md` already documents tool discipline; intent block reinforces auto-tool choice

## Phase 3 — Mokli transformation

| Component | Action |
|-----------|--------|
| `App.tsx` | New `ShellView`; routes for performance/briefing/recommendations |
| `Sidebar.tsx` | Gold nav: Performance, Recommendations, Briefing, Chart |
| `TradingPerformance.tsx` | **New** — `/api/trading/performance` |
| `TradingBriefingPanel.tsx` | **New** — full briefing view |
| `TradingChartBottomSheet.tsx` | **New** — mobile chart from `session-store` |
| `TradingInbox.tsx` | Rename labels → Recommendations |
| Remove from shell | `apps`, `automations`, `skills`, `channels` top-level views |

## Phase 4 — Channel delivery

| File | Change |
|------|--------|
| `stage_delivery.py` | `publish_result` → Telegram HTML card + WhatsApp plain text |
| `channels/whatsapp/trading_cards.py` | **New** plain-text card renderer |
| `stage_delivery.py` | WhatsApp Arabic stage checklist (mirror Telegram) |

## Phase 5 — Backend depth (follow-up PRs)

- `orchestrator.py` + `intent_router` fast-path for high-confidence price queries
- G7 reprice loop, drawing agent, LLM synthesizer
- Decision memory `memory/trades.jsonl` + Dream integration
- Real debate/swarm via `spawn` in `crew/debate.py`, `teams/runtime.py`
- HTTPS for `mokli.lork.cloud`

## API surface (existing + new)

| Route | File | Status |
|-------|------|--------|
| `/api/trading/klines` | `trading_api.py` | exists |
| `/api/trading/quote` | | exists |
| `/api/trading/analyze` | | exists |
| `/api/trading/recommendations` | | exists |
| `/api/trading/briefing` | | exists |
| `/api/trading/runtime/update` | | pause/kill/paper |
| `/api/trading/performance` | | **new** |
| WebSocket `agent_ui` | `stage_delivery.py` | `trading_stage`, `trading_result`, `trading_chart_open` |

## Test gates

```bash
pytest tests/trading -q
cd mokli && npm run build
```

## Merge path

1. `cursor/gold-trading-foundation-aba3` → `main`
2. `cursor/gold-trading-phases-aba3` → foundation
3. `cursor/gold-trading-chat-first-aba3` → phases
4. **This branch** `cursor/gold-agent-aichart-aba3` → chat-first (product shell)
