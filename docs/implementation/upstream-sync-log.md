# Upstream sync log (HKUDS/nanobot)

Remote: `nanobot-upstream` → https://github.com/HKUDS/nanobot

| Date | Upstream | Summary | Method | Branch |
|------|----------|---------|--------|--------|
| 2026-09-15 | `151173c8` | Session: search older history pages | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `8c4eb2c8` | Session: bound retained search results | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `f4843ba1` | Memory: recover archive tool calls | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `0374f74b` | Providers: assistant content + tool calls | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `e5a13795` | Responses API: clean replayed items | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `02ca8f65` | Cron: defer timer rearm during jobs | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `60b7c8cf` | Cron: recheck pending before execute | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `93b51121` | Cron: preserve pending on edit | manual port | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `95b2346e` | WebUI: markdown tables in file preview | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |
| 2026-09-15 | `7cede64f` | WebUI: reasoning preview perf | cherry-pick | cursor/sync-nanobot-upstream-c0e8 |

## Skipped (conflict or empty)

| Upstream | Reason |
|----------|--------|
| `0c5d8443` | OpenAI Responses converters conflict with fork |
| `d386ba13`, `1c3c6826`, `3a725b35` | Filesystem / file_state fork diverged |
| `55093dd7` | Empty cherry-pick (likely already present) |
| `73410e02` | Conflicts with memory.py after `f4843ba1` |
| `f611c880` | ThreadShell trading UI conflict |

## Next candidates

- `ddd6b302` — remote project paths (WebUI, review conflict)
- `08b130cd` — mobile context sheet (WebUI)
- Manual port of `d386ba13` dedup scope into `file_state.py`
