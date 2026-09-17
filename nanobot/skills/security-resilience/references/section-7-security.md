# Security and resilience

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| section-7-security | `section-7-security.md` | — | section narrative |


Table of contents: Master kill switch · Encrypted local credentials · Local ticket restore · Bad tick filter · Adopt manual positions

### Master kill switch

One operator command: propose flatten of gold positions, cancel pendings, halt new proposals. Confirm unless the dedicated emergency path is already armed. Do not keep "just one scalp."

### Encrypted local credentials

MetaAPI and broker secrets live in local env, never in chat, skills, or screenshots.

### Local ticket restore

Persist tickets and management state in local SQLite. After a crash, reload opens before any new risk. Unmanaged broker tickets are adopt candidates — never attach stops without a yes.

### Bad tick filter

DETERMINISTIC: ignore a print that jumps more than `live().BAD_TICK_POINTS` and snaps back. INTERPRETIVE: do not call it a breakout.

### Adopt manual positions

If the operator (or phone) opens gold manually, ask once to adopt management. Never attach stops to a stranger ticket without that yes.
