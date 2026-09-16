---
name: xauusd-playbook
description: Lonora 200-rule XAUUSD field playbook — flexible entries, stop philosophy, retests, trendlines, gold-specific liquidity, take-profit, candle traps, and execution discipline. Use during analysis, management, or when the operator challenges a wait, a stop, or a missed fill. English skill; reply in the operator's language.
---

# XAUUSD playbook (200 rules)

Grep `P-NNN` (zero-padded) in `references/` rather than loading every section.

## References

- [references/playbook-001-025-entry.md](references/playbook-001-025-entry.md)
- [references/playbook-026-055-stops.md](references/playbook-026-055-stops.md)
- [references/playbook-056-080-retest.md](references/playbook-056-080-retest.md)
- [references/playbook-081-105-trendlines.md](references/playbook-081-105-trendlines.md)
- [references/playbook-106-135-gold-liquidity.md](references/playbook-106-135-gold-liquidity.md)
- [references/playbook-136-160-targets.md](references/playbook-136-160-targets.md)
- [references/playbook-161-180-candle-traps.md](references/playbook-161-180-candle-traps.md)
- [references/playbook-181-200-discipline.md](references/playbook-181-200-discipline.md)
- Execution, memory, alerts, security, and multi-tasking: sibling skills `mt5-execution`, `memory-review`, `security-resilience`, `multi-tasking-scenarios`, plus `trading-proactive`

## Steps

1. Decide INTERPRETIVE vs DETERMINISTIC. If the rule has a `live()` owner, obey the gate; use the playbook text only as judgment around it.
2. Entries may be immediate, anticipatory, or conditional. Do not require a classic S/R touch (P-001) or a retest (P-056) when momentum already completed the sweep.
3. Stops sit beyond liquidity, not on the obvious swing (P-026). Invalidation is structural (P-031). Never widen a live stop (P-035).
4. Recommendations stay recommendations until the operator confirms a MetaAPI proposal. P-182 auto-send is excluded.

## Output

- Which playbook ids support the plan.
- What would cancel the idea (time, half-distance, structure, news).
- Compact operator language; no gate ids.

## Example

Operator: "wait for the retest of 3350."
You: "A retest is not mandatory on gold explosions (P-056). If H1 already ran and the pullback would consume the whole target (P-003), enter with momentum or stand aside — do not fade into a 1:1 trap."

## Do not

- Duplicate live numeric caps in the reply.
- Describe unshown timeframes.
- Open a second live recommendation in the same conversation.
