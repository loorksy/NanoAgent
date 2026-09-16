# Spec section 8 — Multi-tasking and scenarios

Table of contents: `S8.1` Scan while managing · `S8.2` Dual scenarios · `S8.3` Scalp vs swing · `S8.4` Natural language · `S8.5` Toggles

### S8.1 — Scan while an idea is live

Async is allowed: manage the open plan and keep reading gold. Do not publish a second live card in the same conversation. Follow-ups are opinions on the live plan (`get_live_recommendation`).

### S8.2 — Break vs fail pair

Two conditionals may exist: buy if the level breaks and holds, sell if it fails. The first confirmed scenario activates; the other is cancelled. Never fill both.

### S8.3 — Scalp vs swing isolation

Separate magic numbers (`MAGIC_SCALP`, `MAGIC_SWING`). Do not trail a swing with a scalp stop or add a scalp loser onto a swing.

### S8.4 — Natural-language orders

Translate "move every gold stop to entry if we touch X" into a concrete proposal, then HITL. Do not silently batch-modify.

### S8.5 — Feature toggles

Operator toggles on the Risk Parameters page may skip named gates (news shield, cooldown, …). Confirm is never a toggle. If a protection is off, say so in user-facing language.
