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

| Skill | Description |
|-------|-------------|
| `gold-trading` | Gold (XAUUSD) recommendation/execution constitution |
| `trading-proactive` | When to notify vs stay silent for gold ops |
| `gold-entry-timing` | Field rules 1–25 — entry flexibility |
| `gold-stop-protection` | Field rules 26–55 — stops & protection |
| `gold-retest` | Field rules 56–80 — retest philosophy |
| `gold-trendlines` | Field rules 81–105 — trendlines & channels |
| `gold-xauusd-dynamics` | Field rules 106–135 — gold session/liquidity quirks |
| `gold-take-profit` | Field rules 136–160 — targets & harvest |
| `gold-candle-traps` | Field rules 161–180 — candle traps |
| `gold-execution-discipline` | Field rules 181–200 — execution discipline |
| `gold-news-volatility` | News/volatility operating rules 1–100 |
| `gold-news-candle-detection` | News-candle detection rules 1–100 |
| `cron` | Schedule reminders and recurring tasks |
| `memory` | Long-term memory guidance |
| `github` | Interact with GitHub using the `gh` CLI |
| `weather` | Get weather info using wttr.in and Open-Meteo |
| `summarize` | Summarize URLs, files, and YouTube videos |
| `tmux` | Remote-control tmux sessions |
| `clawhub` | Search and install skills from ClawHub registry |
| `skill-creator` | Create new skills |

Gold field encyclopedias above total **400** numbered rules. Index: `docs/prompts/rulebooks/README.md`.
