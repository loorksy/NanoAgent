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

```bash
/workspace/.venv/bin/mokli gateway --background --port 18791
# Agent API default 8766 when gateway runs with agentApi enabled
cd /workspace/mokli-ui && bun run dev --host 127.0.0.1 --port 5173
curl -s http://127.0.0.1:5173/api/v2/health
bash scripts/mokli_upgrade_preflight.sh  # API health + config warn; no LLM call
/workspace/.venv/bin/pytest tests/agent tests/trading tests/agent_api tests/deploy/test_mokli_pipe.py tests/scripts/test_mokli_upgrade_diagnostic_extract.py tests/scripts/test_mokli_upgrade_preflight.py -q
python scripts/mokli_upgrade_diagnostic_extract.py --file events.jsonl  # after live turn with SHOW_DIAGNOSTICS
```

Aggregate pytest target: 2296 passed. Live chat paths (no-tools turn, gold analysis, paper trading, phone/desktop UI) require operator keys and deploy; fill `docs/mokli-agent-upgrade-report.md` §11 before marking the upgrade complete.
- Tests mirror the `mokli/` package structure.
