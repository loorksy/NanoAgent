---
name: memory-review
description: Gold self-review — similar historical cases, post-mortem after a loss, lesson log, and dual technical-plus-risk review before a proposal. Quick historical replay / backtest is excluded. Use after a stop-out, before repeating a setup, or when the operator asks "have we seen this?". English skill; reply in the operator's language.
---

# Memory and review (gold)

## References

- Memory and review: [references/section-5-memory.md](references/section-5-memory.md)
- Engines: FEATURE-06 vector playbook, FEATURE-07 FastDTW (live chart only — not the excluded historical backtest), FEATURE-08 SQLite post-mortem
- **Quick historical replay excluded:** no historical candle replay / backtest loop

## Steps

1. Before a new plan, query post-mortem for the last similar losses (spread, session, pattern). If it repeats yesterday's error, refuse and say so in operator language.
2. Use vector/DTW as supporting similarity, not as a side flip.
3. After a loss: record expected vs actual, whether the exit followed the plan, and the lesson. Be blunt (admit the error).
4. Dual review: technical idea plus risk math. Both must agree before a proposal.

## Output

- Similar-case note (or "no match").
- If blocked: the repeated mistake in one sentence.
- After a loss: what the market hunted, in numbers from tools.

## Example

Operator: "same long as yesterday?"
You: "Post-mortem flags yesterday's long as an Asia-high buy-stop through the London sweep. This print rhymes. I will not propose it."

## Do not

- Invent a 500-scenario memory that is not in the store.
- Shame the operator. State the error and the next constraint.
