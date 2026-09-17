# Risk guardrails

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| section-3-risk | `section-3-risk.md` | — | section narrative |


Table of contents: Automatic lot sizing · Daily drawdown breaker · Spread guard · Cooldown lock · Maximum open positions · Minimum reward-to-risk

Every numeric cap below is **DETERMINISTIC**. Quote `policy.live()` / the matching gate. Do not paste default percents into operator chat as if they were eternal.

### Automatic lot from risk percent and stop

Lot so that stop distance equals the configured risk fraction of **balance**. News-day risk is a separate live field. Dual-check the lot against high/low sanity bounds (P-188). Grow size from closed balance, not floating equity (P-199). Inverse-size when ATR doubles (N-067). Owner: position sizing / `evaluate_position_sizing`.

### Daily drawdown breaker

When daily loss reaches the live drawdown percent, block new gold risk until the next day. Flattening live positions is an execution-path action and still needs HITL unless kill-switch policy says otherwise. Owner: daily drawdown breaker.

### Spread guard

If bid/ask width exceeds the live point cap, veto. Require the live stable-seconds before re-enabling. Pre-news 3x normal spread is a separate live check. Owner: spread guard.

### Cooldown after consecutive losses

After the configured consecutive losses, lock new entries for the live cooldown minutes (cooldown lock vs playbook 187: the code uses the stricter/max policy). News stop-outs use a separate live cooldown. Owner: cooldown lock.

### Max open gold positions

Cap concurrent gold positions at the live max. `0` means no cap. Do not add a same-side loser (P-184). Owner: max positions.

### Minimum reward-to-risk

Farthest target must meet `live().MIN_RR` (rec path). Live fill uses `MIN_RR_LIVE_FILL` on confirm (P-196). TP1 at 1:1 plus TP2 at 1:2 can pass because the farthest target is used. Owner: reward-to-risk filter.

## INTERPRETIVE wrap

If the operator edits Risk Parameters, the next evaluation uses the new values. Do not refuse a legally in-range number. HITL confirm stays on.
