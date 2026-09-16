# nanobot Skills

This directory contains built-in skills that extend nanobot's capabilities.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with:
- YAML frontmatter (name, description, metadata)
- Markdown instructions for the agent
- **English only** in skill files (no Arabic or other non-Latin scripts in `SKILL.md` bodies, examples, or identifiers). Operator-facing replies still use the operator's language at runtime.

When skills reference large local documentation or logs, prefer nanobot's built-in
`grep` tool to narrow the search space before loading full files.
Use `grep(output_mode="count")` / `files_with_matches` for broad searches first,
use `head_limit` / `offset` to page through large result sets,
and `grep(glob="*.md")` to filter by file name pattern.

## Attribution

These skills are adapted from [OpenClaw](https://github.com/openclaw/openclaw)'s skill system.
The skill format and metadata structure follow OpenClaw's conventions to maintain compatibility.

## Available Skills

Built-in directories are auto-discovered from this folder (`SKILL.md` required). Large gold encyclopedias live in each skill's `references/` — grep by id (`P-056`, `N-035`, `C-016`) rather than loading whole files. Operator-facing strings stay in `nanobot/trading/i18n.py`.

| Skill | Description |
|-------|-------------|
| `gold-trading` | Lonora constitution (gold-only, recs vs HITL, tools) |
| `technical-analysis` | Technical and price action (FVG, MTF, sweeps, BOS/CHoCH) |
| `macro-radar` | Macro radar (calendar, DXY, tone, geopolitics) |
| `risk-guardrails` | Risk guardrails around `policy.live()` |
| `mt5-execution` | Execution and trade management (MetaAPI propose/confirm; HITL mandatory) |
| `memory-review` | Memory and review (similar cases, post-mortem, dual review) |
| `news-volatility-protocol` | 100 news rules + 100 news-candle rules |
| `xauusd-playbook` | 200 operational field rules |
| `security-resilience` | Security and resilience (kill switch, bad ticks, restore) |
| `multi-tasking-scenarios` | Multi-tasking and scenarios (dual scenarios, scalp vs swing, toggles) |
| `trading-proactive` | When to notify; silence in a dead market |
| `memory` | Search `history.jsonl` |
| `cron` | Scheduled tasks |
| `github` | Interact with GitHub using the `gh` CLI |
| `weather` | Get weather info using wttr.in and Open-Meteo |
| `summarize` | Summarize URLs, files, and YouTube videos |
| `tmux` | Remote-control tmux sessions |
| `clawhub` | Search and install skills from ClawHub registry |
| `skill-creator` | Create new skills (packaged upstream; may be absent in this tree) |

Coverage table: `gold-trading/references/coverage.md`.
