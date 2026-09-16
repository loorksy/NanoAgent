# Spec section 7 — Security and resilience

Table of contents: `S7.1` Kill switch · `S7.2` Secrets · `S7.3` Restore · `S7.4` Bad tick · `S7.5` Manual adopts

### S7.1 — Master kill switch

One operator command: propose flatten of gold positions, cancel pendings, halt new proposals. Confirm unless the dedicated emergency path is already armed. Do not keep "just one scalp."

### S7.2 — Encrypted local credentials

MetaAPI and broker secrets live in local env, never in chat, skills, or screenshots.

### S7.3 — Local ticket restore

Persist tickets and management state in local SQLite. After a crash, reload opens before any new risk. Unmanaged broker tickets are adopt candidates — never attach stops without a yes.

### S7.4 — Bad tick filter

DETERMINISTIC: ignore a print that jumps more than `live().BAD_TICK_POINTS` and snaps back (G16). INTERPRETIVE: do not call it a breakout.

### S7.5 — Adopt manual positions

If the operator (or phone) opens gold manually, ask once to adopt management. Never attach stops to a stranger ticket without that yes.
