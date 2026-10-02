This file provides guidance to AI coding agents working with this repository.

## Project Overview

mokli is a lightweight, open-source AI agent framework written in Python. The browser client is the Mokli fork in `mokli-ui/`. It centers around a small agent loop that receives messages from chat channels, invokes an LLM provider, executes tools, and manages session memory.

## Development Commands

```bash
# Python: run single test / lint
pytest tests/test_openai_api.py::test_function -v
ruff check mokli/

# Strict type checking (matches CI)
uv sync --all-extras --dev
uv run --no-sync python -m scripts.install_channel_dependencies --all-channels
uv run --no-sync basedpyright

# Browser client (Open WebUI fork in mokli-ui/). Charting library assets remain at
# mokli-ui/public/charting_library/.
cd mokli-ui && bun run dev --host 127.0.0.1 --port 5173
cd mokli-ui && npm run build

# Gateway
mokli gateway
```

## High-Level Architecture

### Core Data Flow

Messages flow through an async `MessageBus` (`mokli/bus/queue.py`) that decouples chat channels from the agent core:

1. **Channels** (`mokli/channels/`) receive messages from external platforms and publish `InboundMessage` events to the bus.
2. **`AgentLoop`** (`mokli/agent/loop.py`) consumes inbound messages, builds context, and coordinates the turn.
3. **`AgentRunner`** (`mokli/agent/runner.py`) handles the actual LLM conversation loop: send messages to the provider, receive tool calls, execute tools, and stream responses.
4. Responses are published as `OutboundMessage` events back to the appropriate channel.

### Key Subsystems

- **Agent Loop** (`mokli/agent/loop.py`, `runner.py`): The core processing engine. `AgentLoop` manages session keys, hooks, and context building. `AgentRunner` executes the multi-turn LLM conversation with tool execution.
- **LLM Providers** (`mokli/providers/`): Provider implementations (Anthropic, OpenAI-compatible, OpenAI Responses API, Azure, Bedrock, GitHub Copilot, OpenAI Codex, etc.) built on a common base (`base.py`). Includes image generation (`image_generation.py`) and audio transcription (`transcription.py`). `factory.py` and `registry.py` handle instantiation and model discovery.
- **Channels** (`mokli/channels/`): Platform integrations (Telegram, Discord, Slack, Feishu, Matrix, WhatsApp, QQ, WeChat, WeCom, DingTalk, Email, MoChat, MS Teams, WebSocket, Mattermost). `manager.py` discovers and coordinates them. Channels are self-contained packages auto-discovered via `pkgutil` scanning.
- **Tools** (`mokli/agent/tools/`): Agent capabilities exposed to the LLM: filesystem (read/write/edit/list), shell execution (with sandbox backends), web search/fetch, MCP servers, cron, notebook editing, subagent spawning, long-running tasks / sustained goals (`long_task.py`), image generation, and self-modification. Tools are auto-discovered via `pkgutil` scan + entry-point plugins.
- **Memory** (`mokli/agent/memory.py`): Session history persistence with Dream two-phase memory consolidation. Uses atomic writes with fsync for durability.
- **Session Management** (`mokli/session/`): Per-session history, context compaction, TTL-based auto-compaction (`manager.py`), and sustained goal state tracking (`goal_state.py`).
- **Config** (`mokli/config/schema.py`, `loader.py`): Pydantic-based configuration loaded from `~/.mokli/config.json`. Supports camelCase aliases for JSON compatibility.
- **Mokli** (`mokli/`): Vite-based React SPA that talks to the gateway over a WebSocket multiplex protocol. The dev server proxies `/api`, `/mokli`, `/auth`, and WebSocket traffic to the gateway.
- **API Server** (`mokli/api/server.py`): OpenAI-compatible HTTP API (`/v1/chat/completions`, `/v1/models`) for programmatic access.
- **Command Router** (`mokli/command/`): Slash command routing and built-in command handlers.
- **Heartbeat** (`mokli/templates/HEARTBEAT.md`): Periodic task list checked via `cron` jobs (legacy dedicated service removed).
- **Pairing** (`mokli/pairing/`): DM sender approval store with persistent pairing codes per channel.
- **Skills** (`mokli/skills/`): Built-in skill definitions (cron, github, image-generation, etc.) loaded into agent context.
- **Security** (`mokli/security/`): PTH file guard and other security measures activated at CLI entry.

### Entry Points

- **CLI**: `mokli/cli/commands.py`
- **Python SDK**: `mokli/mokli.py`

## Project-Specific Notes

- Architecture constraints: [`.agent/design.md`](.agent/design.md)
- Security boundaries: [`.agent/security.md`](.agent/security.md)
- Common gotchas: [`.agent/gotchas.md`](.agent/gotchas.md)

## Contribution Flow

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for contribution flow and PR guidelines.

## Code Style

- Python 3.11+, asyncio throughout.
- Line length: 100.
- Linting: `ruff` with rules E, F, I, N, W (E501 ignored).
- pytest with `asyncio_mode = "auto"`.

## Common File Locations

- Config schema: `mokli/config/schema.py`
- Provider base / new provider template: `mokli/providers/base.py`
- Channel base / new channel template: `mokli/channels/base.py`
- Tool registry: `mokli/agent/tools/registry.py`
- Mokli dev proxy config: `mokli-ui/vite.config.ts` (default `MOKLI_BACKEND_URL=http://localhost:8766`)

## Cursor Cloud specific instructions

Mokli upgrade work on this repo often cannot reach live LLM, OANDA, or MetaAPI keys. Prefer measured unit tests and local smoke without inventing credentials.

VPS deploy from Cloud Agent: set environment secrets **`VPS`** (host or `user@host`) and **`VPSPASS`** (SSH password). Legacy names `vps` / `password` are mapped by `scripts/vps_env.sh`. Verify with `bash scripts/cloud_agent_vps_secrets_check.sh` (registered-but-empty injection → start a new agent run). Key-based: `MOKLI_SSH_HOST=… bash scripts/vps_pull_main.sh`. Password: `MOKLI_BRANCH=main bash scripts/deploy-mokli-vps.sh`.

```bash
/workspace/.venv/bin/mokli gateway --background --port 18791
# Agent API default 8766 when gateway runs with agentApi enabled
cd /workspace/mokli-ui && bun run dev --host 127.0.0.1 --port 5173
curl -s http://127.0.0.1:5173/api/v2/health
bash scripts/mokli_upgrade_operator_smoke.sh  # preflight + §11 dry-run + init smoke + tests/scripts (no LLM)
bash scripts/mokli_upgrade_section11_cloud_status.sh  # quota cache + VPS env + blockers @13 (exit 1 until closure)
bash scripts/mokli_upgrade_section11_cloud_status.sh --require-through 10  # exit 0 when local JSONL 1–10 OK (quota may still block)
bash scripts/mokli_upgrade_section11_operator_unblock.sh  # live probe + env + blockers @13
bash scripts/mokli_upgrade_section11_operator_unblock.sh --skip-probe  # cached quota only (quota already blocked)
# Paid §11 model from workstation: export MOKLI_SECTION11_MODEL=… before vps_section11_* (forwarded over SSH)
bash scripts/vps_section11_quota_status.sh  # read last quota-probe JSONL (no LLM call; prints OpenRouter reset hint)
bash scripts/mokli_upgrade_section11_wait_quota_reset.sh  # seconds until reset; --wait sleeps then quota_probe
bash scripts/mokli_upgrade_section11_init.sh  # VPS: scaffold events/ + results + progress (no LLM)
bash scripts/mokli_upgrade_preflight.sh  # API health + config warn; no LLM call
bash scripts/mokli_upgrade_aggregate_pytest.sh
python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl  # after live turn with SHOW_DIAGNOSTICS
# Operator §11 pack (after VPS live runs): docs/section11-results.example.json → section11-results.json
bash scripts/mokli_upgrade_section11_dry_run.sh  # fixture row 1 only; not production closure
bash scripts/mokli_upgrade_section11_validate.sh --dir ./section11-events --results section11-results.json
bash scripts/mokli_upgrade_section11_post_quota.sh --wait --pull-vps # before/at reset: wait + probe + partial reruns
bash scripts/mokli_upgrade_section11_after_reset_wake.sh # after reset: probe + partial reruns (no long sleep)
bash scripts/mokli_upgrade_section11_completion_status.sh # cached quota + §11 @13 (+ partial10 gate when blocked)
bash scripts/mokli_upgrade_section11_cloud_status.sh # quota snapshot + blockers @13 (+ partial10_ok/gate)
bash scripts/mokli_upgrade_operator_smoke.sh  # preflight + §11 dry-run + production_gate @10 on partial pack
bash scripts/mokli_upgrade_section11_timer_wake.sh --dry-run # cached status; after reset: --wait-quota then full chain @13
bash scripts/mokli_upgrade_section11_sync_cloud_branch.sh  # git pull §11 branch before wake (also inside timer_wake / after_reset_wake)
# Background on Cloud Agent VM (sleep until reset, then VPS reruns): tmux session section11-timer-wake-wait → log /opt/cursor/artifacts/timer_wake_wait_quota.log
bash scripts/mokli_upgrade_section11_check_wake.sh  # tmux + log tail + blockers_summary (no LLM)
bash scripts/mokli_upgrade_section11_monitor_log.sh  # append check_wake snapshot to section11_monitor.log
# Production validate @13: rejects PARTIAL in results; requires section11-events/01-no-tools-after-p0.jsonl (--allow-partial for preview only)
bash scripts/mokli_upgrade_section11_status.sh  # exit 0 when artifacts + VPS quota probe OK (set MOKLI_SSH_HOST)
bash scripts/mokli_upgrade_section11_status.sh --skip-quota  # validate JSONL/results only (no LLM call)
bash scripts/mokli_upgrade_section11_close.sh  # dry-run; --apply --require-through 13 --results section11-results-partial.json after live artifacts
# Partial pack preview: --results section11-results-partial.json --require-through 10 --allow-partial (no --apply)
# Preview §11 table with partial VPS pack: close.sh --results section11-results-partial.json --require-through 10 --allow-partial (no --apply)
bash scripts/mokli_upgrade_section11_sync_from_vps.sh --pull-vps  # pull JSONL + after_pull (P0 delta even when validate @13 fails); pass EVENTS RESULTS 13
bash scripts/vps_section11_row1_after_p0.sh  # after VPS quota probe OK
bash scripts/mokli_upgrade_section11_rerun_partials.sh  # selective gaps from validate --print-live-rerun-rows (+ OANDA for 10)
bash scripts/mokli_upgrade_section11_precheck_ui.sh  # rows 12–13 UI prechecks (no LLM; VPS SSH for :8080)
bash scripts/mokli_upgrade_section11_blockers.sh  # env + validate 13; exit 0 only when closable
bash scripts/mokli_upgrade_section11_production_gate.sh --skip-quota --skip-oanda --skip-pull --require-through 10  # artifact pack while quota blocked
# Completion gate matrix: docs/mokli-agent-upgrade-completion-audit.md
```

Aggregate pytest target: 2532 passed (1 skipped). Live chat paths (no-tools turn, gold analysis, paper trading, phone/desktop UI) require operator keys and deploy; fill `docs/mokli-agent-upgrade-report.md` §11 before marking the upgrade complete. Rows 11–13 runbook: `bash scripts/mokli_upgrade_section11_remaining_rows.sh`.

While OpenRouter quota is blocked (`vps_section11_quota_probe.sh` → `in=0`): prefer `check_wake.sh`, `monitor_log.sh`, or `completion_status.sh` monitoring only—avoid audit `git_rev`-only commits and repeated operator-smoke unless the branch changed. If `git push` fails, sync §11 script fixes to VPS with `bash scripts/vps_section11_scp_branch_scripts.sh` until the branch tip is on origin. Optional tmux `section11-monitor-loop` runs `bash scripts/mokli_upgrade_section11_monitor_loop.sh` (30m default). `timer_wake` (non dry-run) holds `flock` on `/tmp/mokli_section11_timer_wake.lock` and logs `TIMER_WAKE_FINAL_EXIT` on exit; a second concurrent run exits 2. MCP one-shot timers (e.g. `mokli-section11-at-reset-buffer`, `mokli-section11-after-openrouter-reset-backup`) can wake the agent after `wake_after_buffer_utc` if tmux dies. After `wake_after_buffer_utc`: `timer_wake` (or `after_reset_wake` if probe already OK), then operator `vps_section11_set_oanda_env.sh` and `remaining_rows.sh` for 11–13 before `close.sh --apply @13`.
- Tests mirror the `mokli/` package structure.
