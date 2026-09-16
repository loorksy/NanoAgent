---
name: news-volatility-protocol
description: Gold news and shock protocol — pre-print freeze, reading the print, news-candle anatomy, spread/slippage safety, post-news trend ride, and unscheduled geopolitics, plus the 100-rule news-candle encyclopedia. Use around CPI, NFP, FOMC, spikes, wicks, or unexplained 1-minute explosions. English skill; reply in the operator's language.
---

# News and volatility protocol (gold)

Two encyclopedias live here. Grep by id (`N-014`, `C-016`) before loading a whole file.

## References

- [references/news-100.md](references/news-100.md) — operational news rules `N-001` … `N-100`
- [references/news-candles-100.md](references/news-candles-100.md) — candle detection `C-001` … `C-100`

Numeric freeze, void, spread, slippage, ADR-chase, and candle ATR/volume z-scores are DETERMINISTIC (`policy.live()`, news and event shield, spread guard, session and calendar lock, news operational freeze, slippage and latency, news-candle helpers).

## Steps

1. If the calendar marks high-impact inside the live blackout, do not issue a new recommendation (news and event shield is stricter than news rule 1).
2. First 60 seconds after a print is a dead void (N-035). Do not interpret the first tick as the day's trend.
3. Classify the candle with C-rules (time sync, range vs ATR, tick volume, spread, intermarket, morphology). If ATR, volume, and spread all explode, treat as a news candle even with an empty calendar (C-100).
4. Geopolitical panic: technical shorts are off (N-087, N-088). De-escalation headlines invalidate the panic long (N-093).

## Output

- Phase: pre-print / void / post-print structure / geopolitics.
- Whether the operator must wait.
- The INTERPRETIVE read of the news candle (sweep vs trend) after DETERMINISTIC checks pass.

## Example

Operator: "CPI wick sold off 80 points, sell now?"
You: "That first minute is a void. If M5 closes as a long upper wick after sweeping the pre-news high, the INTERPRETIVE read is a trap — still wait until the freeze after-window clears."

## Do not

- Chase a 200% ADR news impulse (N-082).
- Place buy-stop/sell-stop through the print (N-017).
- Call every wide candle a news candle on Asia lunch without time, volume, or spread confirmation.
