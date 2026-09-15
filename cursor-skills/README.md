# Cursor Skills

Optional skills for Cursor agents, installed into `~/.cursor/skills/`.

## Install

From the repository root:

```bash
./scripts/install-cursor-skills.sh
```

This symlinks each folder under `cursor-skills/` into your user skills directory.

## Included skills

| Skill | Purpose |
|-------|---------|
| `claude-fable-cursor` | Behavioral guidelines adapted from Claude Fable 5.1 for Cursor coding agents |

After install, the agent discovers skills via `<available_skills>` and should read `SKILL.md` when starting non-trivial work.

## Source

`claude-fable-cursor` is adapted from the leaked [Claude Fable 5.1 system prompt](https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-fable-5.1.md), remapped for Cursor tooling (Read/Edit/Shell, subagents, MCP, PR tools) — not Anthropic chat products.
