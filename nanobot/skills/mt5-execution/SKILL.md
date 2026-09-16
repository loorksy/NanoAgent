---
name: mt5-execution
description: Gold MetaAPI/MT5 human-in-the-loop execution — propose, confirm, trailing, breakeven, partials, news shield, and early-exit judgment. Use when the operator wants to place, modify, or close a gold order, or asks why a proposal expired. English skill; reply in the operator's language.
---

# MT5 execution (HITL)

Analysis tools never send orders. Execution tools only propose; the operator must confirm. That confirm flag is not WebUI-disableable.

## References

- Execution and trade management: [references/section-4-execution.md](references/section-4-execution.md)
- Playbook management/discipline: `P-136` … `P-160`, `P-181` … `P-200`

## Steps

1. Build the recommendation first. If rec gates fail, do not propose.
2. Propose a bracket (entry, SL, TPs) with TTL from `live().PROPOSAL_TTL_SECONDS`. If TTL lapses, re-propose — do not silently send.
3. On confirm, re-check live fill reward-to-risk (`MIN_RR_LIVE_FILL`), spread, slippage, stale quote, and session locks.
4. Management (trail, BE, partials, news shield, early exit) is INTERPRETIVE around DETERMINISTIC buffers. Recommend or, after confirm, request a modify — never hidden auto-trade.

## Output

- Proposal summary in operator language.
- Expiry and what they must tap to confirm.
- After fill: next management step only.

## Example

Operator: "send it."
You: "Proposal is ready: buy limit at the bid, stop beyond the sweep low, two targets. Confirm in the next TTL window or it expires. I will not send without that confirm."

## Do not

- Follow playbook 182 (zero-hesitation without a human).
- Martingale into a news spike.
- Mix scalp and swing magic numbers (P-185).
