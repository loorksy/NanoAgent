# Multi-tasking and scenarios

Table of contents: Scan while managing · Dual scenarios · Scalp vs swing · Natural-language orders · Feature toggles

### Scan while an idea is live

Async is allowed: manage the open plan and keep reading gold. Do not publish a second live card in the same conversation. Follow-ups are opinions on the live plan (`get_live_recommendation`).

### Break vs fail pair

Two conditionals may exist: buy if the level breaks and holds, sell if it fails. The first confirmed scenario activates; the other is cancelled. Never fill both.

### Scalp vs swing isolation

Separate magic numbers (`MAGIC_SCALP`, `MAGIC_SWING`). Do not trail a swing with a scalp stop or add a scalp loser onto a swing.

### Natural-language orders

Translate "move every gold stop to entry if we touch X" into a concrete proposal, then HITL. Do not silently batch-modify.

### Feature toggles

Operator toggles on the Risk Parameters page may skip named gates (news shield, cooldown, …). Confirm is never a toggle. If a protection is off, say so in user-facing language.
