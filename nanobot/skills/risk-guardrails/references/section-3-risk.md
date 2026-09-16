# Spec section 3 — Risk guardrails

Table of contents: `S3.1` Lot · `S3.2` Daily DD · `S3.3` Spread · `S3.4` Cooldown · `S3.5` Max positions · `S3.6` Min RR

Every numeric cap below is **DETERMINISTIC**. Quote `policy.live()` / the matching gate. Do not paste default percents into operator chat as if they were eternal.

### S3.1 — Automatic lot from risk percent and stop

Lot so that stop distance equals the configured risk fraction of **balance**. News-day risk is a separate live field. Dual-check the lot against high/low sanity bounds (P-188). Grow size from closed balance, not floating equity (P-199). Inverse-size when ATR doubles (N-067). Owner: G20 / `evaluate_position_sizing`.

### S3.2 — Daily drawdown breaker

When daily loss reaches the live drawdown percent, block new gold risk until the next day. Flattening live positions is an execution-path action and still needs HITL unless kill-switch policy says otherwise. Owner: G12.

### S3.3 — Spread guard

If bid/ask width exceeds the live point cap, veto. Require the live stable-seconds before re-enabling. Pre-news 3x normal spread is a separate live check. Owner: G9.

### S3.4 — Cooldown after consecutive losses

After the configured consecutive losses, lock new entries for the live cooldown minutes (section 3.4 vs playbook 187: the code uses the stricter/max policy). News stop-outs use a separate live cooldown. Owner: G10.

### S3.5 — Max open gold positions

Cap concurrent gold positions at the live max. `0` means no cap. Do not add a same-side loser (P-184). Owner: G11.

### S3.6 — Minimum R:R

Farthest target must meet `live().MIN_RR` (rec path). Live fill uses `MIN_RR_LIVE_FILL` on confirm (P-196). TP1 at 1:1 plus TP2 at 1:2 can pass because the farthest target is used. Owner: G8.

## INTERPRETIVE wrap

If the operator edits Risk Parameters, the next evaluation uses the new values. Do not refuse a legally in-range number. HITL confirm stays on.
