---
name: multi-tasking-scenarios
description: Gold multi-task doctrine — manage an open idea while scanning, mutually exclusive break/fail scenarios, scalp vs swing isolation, natural-language orders, and feature toggles. Use when the operator wants two plans, a watch plus a live trade, or to turn a skill off. English skill; reply in the operator's language.
---

# Multi-tasking and scenarios (gold)

## References

- Multi-tasking and scenarios: [references/section-8-scenarios.md](references/section-8-scenarios.md)
- One live recommendation per conversation remains the constitution (`gold-trading`)

## Steps

1. One published live recommendation per conversation. A second scenario stays conditional and unpublished until the first is archived or the operator confirms `force_new_plan`.
2. Break-or-fail pairs: only the confirmed scenario activates; the other is cancelled. Do not run both.
3. Scalp vs swing: separate magic numbers and stops (P-185). Do not trail a swing with a scalp stop.
4. Natural-language orders ("move every gold stop to entry if we touch X") become an explicit proposal, then HITL confirm.
5. Toggles skip some gates; they never skip confirm. Say which protection is off, in user-facing language.

## Output

- What is live vs conditional.
- Which scenario would cancel the other.
- Toggle state if the operator changed one.

## Example

Operator: "buy the break, sell the fail."
You: "I can hold both as conditionals. The first M15 close outside the range activates one and kills the other. I will not publish two live cards."

## Do not

- Answer WAIT as the analytical side — the side is still BUY or SELL; the platform may refuse to publish.
- Enable both legs as live orders.
