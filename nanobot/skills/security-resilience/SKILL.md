---
name: security-resilience
description: Gold runtime safety — kill switch, credential hygiene, local ticket restore, bad-tick filter, and optional adoption of the operator's manual MT5 positions. Use on disconnects, spikes, emergency stop, or "flatten everything." English skill; reply in the operator's language.
---

# Security and resilience (gold)

## References

- Spec section 7: [references/section-7-security.md](references/section-7-security.md)
- DETERMINISTIC: bad-tick points, disconnect alert seconds (`policy.live()`, G13, G16)

## Steps

1. Kill switch: flatten gold via confirmed flatten path, cancel pendings, stop new proposals. Do not argue.
2. Never print secrets from `.env` or MetaAPI tokens.
3. After a restart, restore from local ticket state before proposing new risk.
4. Ignore a one-tick spike that snaps back beyond `live()` bad-tick distance.
5. Manual positions: ask once whether to adopt management; never hijack.

## Output

- Safety state (alive, disconnected, kill-switch).
- What was cancelled or ignored (bad tick).
- Next operator action.

## Example

Operator: "stop everything."
You: "Kill switch path: I will propose flattening opens and cancelling gold pendings. Confirm and I execute; I will not send a new entry."

## Do not

- Treat a bad tick as a breakout (C-021 / N-066).
- Resume entries while kill switch is on.
