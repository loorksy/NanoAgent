# Memory and review

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| section-5-memory | `section-5-memory.md` | — | section narrative |


Table of contents: Similar historical cases · Quick replay (excluded) · Post-trade debrief · Recurring-error lesson file · Dual review

### Similar historical gold cases

Compare current structure and volatility to stored successful gold cases (FEATURE-06). Return similarity and how price behaved then. Supporting evidence only — does not pick BUY vs SELL.

### Quick replay / historical backtest — EXCLUDED

**Excluded.** Quick historical replay is a candle-replay / backtest loop over stored history. Paid APIs and backtest surfaces are out of scope for this agent. Live, forward-only pattern similarity on the *current* chart uses FEATURE-07 FastDTW (`match_pattern`) as supporting evidence — it does not replay past trades or score historical PnL.

### Post-trade debrief

On stop-out, log entry, stop, time, DXY state, break pattern, spread, and the honest cause (FEATURE-08). Tell the operator what was hunted, in numbers.

### Recurring-error lesson file

Persist early-entry, dead-session, and revenge patterns. Before a new proposal, query whether it clones the last few losses; if yes, refuse.

### Dual review (technical + risk)

Technical engine proposes the idea; risk engine checks lot, spread, exposure. Both must pass. A beautiful FVG with illegal reward-to-risk is not published.
