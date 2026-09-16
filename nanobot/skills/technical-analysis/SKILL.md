---
name: technical-analysis
description: Gold XAUUSD price-action doctrine — FVG/imbalance, multi-timeframe structure, sweeps and fakeouts, BOS/CHoCH, Fibonacci premium/discount, tick volume and ATR, RSI/MACD divergence. Use before a buy/sell recommendation, when reading zones or structure, or when the operator asks why a level is valid. English skill; reply in the operator's language.
---

# Technical analysis (gold)

INTERPRETIVE skill. Numeric thresholds live in `nanobot.trading.policy.live()` and the gate chain. Do not invent a second set of numbers.

Read the matching reference with `grep` (`output_mode="count"` first) before loading a whole file:

- Technical and price action: [references/section-1-price-action.md](references/section-1-price-action.md)
- Playbook entry, retest, trendlines, candles: `nanobot/skills/xauusd-playbook/references/` (`P-001` …)

## Steps

1. Higher timeframes first: D1/H4 for path and zones, H1/M15 for timing. Do not fade the higher-timeframe path with a lone M15 pattern (playbook 10, 198).
2. Quote levels from tool output, not from memory. Images confirm shape only.
3. Name the INTERPRETIVE reason (FVG, sweep, BOS, OTE, reclaim) in operator language. Never expose gate ids.
4. If a DETERMINISTIC gate later vetoes, do not flip the side — the plan is unpublished.

## Output

- Bias and path in one sentence.
- The structural reason (zone, sweep, BOS/CHoCH, or imbalance).
- What would invalidate the idea (structure break, not a round-number stop).

## Example

Operator: "why buy here?"
You: "Buy because H4 is still making higher lows, M15 swept equal lows and closed back above the FVG. Invalid if M15 closes below that low."

## Do not

- Restate live risk numbers (spread caps, reward-to-risk floors, freeze windows).
- Require a classic horizontal S/R touch when a trendline or mid-range FVG is the real reaction (playbook 1).
- Describe a timeframe that was not shown.
