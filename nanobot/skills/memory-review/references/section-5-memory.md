# Spec section 5 — Memory and review

Table of contents: `S5.1` Similar cases · `S5.2` Quick replay · `S5.3` Post-trade · `S5.4` Lesson log · `S5.5` Dual review

### S5.1 — Similar historical gold cases

Compare current structure and volatility to stored successful gold cases (FEATURE-06). Return similarity and how price behaved then. Supporting evidence only — does not pick BUY vs SELL.

### S5.2 — Quick replay / historical backtest — EXCLUDED

**Excluded.** Spec 5.2 is a candle-replay / backtest loop over stored history. Paid APIs and backtest surfaces are out of scope for this agent. Live, forward-only pattern similarity on the *current* chart uses FEATURE-07 FastDTW (`match_pattern`) as supporting evidence — it does not replay past trades or score historical PnL.

### S5.3 — Post-trade debrief

On stop-out, log entry, stop, time, DXY state, break pattern, spread, and the honest cause (FEATURE-08). Tell the operator what was hunted, in numbers.

### S5.4 — Recurring-error lesson file

Persist early-entry, dead-session, and revenge patterns. Before a new proposal, query whether it clones the last few losses; if yes, refuse.

### S5.5 — Dual review (technical + risk)

Technical engine proposes the idea; risk engine checks lot, spread, exposure. Both must pass. A beautiful FVG with illegal RR is not published.
