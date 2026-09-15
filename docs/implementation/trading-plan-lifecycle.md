# Trading plan lifecycle framework

## Problem

Follow-up grading could show **invalidated** while SQLite still held a **live** status (`waiting` / `in_trade`). In agent-first mode the LLM calls `analyze_gold`, which blocked on `latest_live_recommendation()` even though the plan was logically closed.

## Principles

1. **Single live row per session** — unchanged; only `valid_now`, `awaiting_activation`, `waiting`, `in_trade` count as live.
2. **Persist before gate** — any graded terminal outcome (`invalidated`, `tp1`, `expired`) is written to SQLite and tagged with `archive_category` before issuing a new recommendation.
3. **Agent-operable** — `manage_trading_plan` exposes sync, prepare, close, and list-archive without starting a new chat.

## Archive categories

| Category | Typical source |
|----------|----------------|
| `invalidated` | Stop loss hit |
| `loss` | Alias when close reason references stop |
| `win` | `tp1` reached |
| `expired` | Validity window ended |
| `superseded` | Operator approved replacement |
| `modified` | Force-new / manual close while still live |
| `other` | Fallback |

## Entry points

- `sync_session_live_plan(session_key)` — grade + persist + archive terminals.
- `prepare_for_new_recommendation(session_key)` — called at start of `analyze_gold`.
- Tools: `get_live_recommendation`, `manage_trading_plan`, `analyze_gold(force_new_plan=…)`.

## Upstream nanobot (HKUDS)

Remote: `nanobot-upstream` → https://github.com/HKUDS/nanobot

This fork adds `nanobot/trading/`, Lonora runtime, WebUI trading surfaces, and heavily modified agent loop. **Do not merge upstream wholesale.** Safe sync process:

1. `git fetch nanobot-upstream main`
2. Compare paths outside `nanobot/trading/`, `webui/src/components/trading`, and fork-specific docs.
3. Cherry-pick or manual port security/ provider fixes only after tests pass.
4. Re-run `pytest tests/trading/` and `uv run basedpyright` on touched modules.

Last checked: 2026-09-15 — upstream main diverges; no automatic merge applied in this change set.
