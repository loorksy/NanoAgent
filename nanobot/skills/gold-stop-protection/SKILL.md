---
name: gold-stop-protection
description: XAUUSD stop-loss placement and protection field rules (26-55). Use when setting, buffering, moving, or refusing to widen stops; also for time stops and news-time SL placement.
---

# Gold Stop Protection Rules (26-55)

## Rules

26. **SL is not the support line:** Placing the stop directly under classic support/swing low is a critical error — that zone is preferred liquidity for stop hunts.
27. **Hit stop as alternate entry:** If SL is tagged by a wick then price closes back inside the range quickly, the prior stop level itself is often the best new entry.
28. **Mandatory buffer zone:** Always add at least 25–40 gold points of buffer beyond swing lows/highs against random noise.
29. **ATR-based stop:** Size stop distance from true volatility (ATR multiple), not a fixed point count.
30. **Stop beyond the impulse candle:** For shorts, place SL above the wick of the break candle, not above a distant historical high.
31. **Structural stop, not fixed points:** Abandon fixed stops (e.g. always 30 points). Place SL where the technical thesis is fully invalidated.
32. **Avoid round-number stops:** Market makers target round figures; prefer odd fractions (e.g. 2447.80 not 2450.00).
33. **Dynamic trendline stop:** In some trades, a close beyond the trendline is the stop criterion rather than a static price.
34. **Tighten after confirmation:** Once price prints a momentum candle in trade direction, pull SL behind that candle’s extreme to cut risk.
35. **Never widen the stop:** Expanding SL after entry to accept larger loss is strictly forbidden.
36. **Time stop:** If gold opens a trade and chops dead for more than 3 hours without expansion, close or tighten — reverse explosion risk rises.
37. **Stop beyond liquidity pools:** Place SL safely beyond equal lows/highs (magnets for wicks).
38. **Breakeven rule:** Move to breakeven only after price travels at least 1R and forms a new M15 swing in favor.
39. **Protect peak profits:** If the trade reaches ~70% of target, place a profit-protect stop near 50% of the move so winners cannot fully reverse to losers.
40. **Order-block buffer:** Place SL ~15 points beyond the institutional order block, not exactly on its edge.
41. **Shorts account for spread:** On sells, widen SL by the closing-time spread so a fake spread spike does not stop you out.
42. **Chandelier / ATR trail:** Use highest high of last N bars minus ATR multiple as a trailing stop.
43. **Asia sweep short stop:** After selling following an Asia liquidity grab, place SL ~10 points above the sweep wick high.
44. **Never park SL inside open FVG:** Do not place stops mid open fair-value gap — price tends to fill the gap fully.
45. **Momentum-break early exit:** Exit if two consecutive M5 closes print against the trade with rising momentum, even before original SL.
46. **Do not BE too early:** Moving to entry before a minor swing is cleared often stops you on a noise wick before the real move.
47. **Portfolio-percent stop:** Entry-to-SL distance must map via lot size to exactly the configured risk % (1% or 2%).
48. **Close-based stop option:** Some setups use “H1 close beyond level” rather than a wick touch.
49. **News-time free zone:** Five minutes before hot news, ensure SL sits clear of liquidity voids to reduce slippage impact.
50. **Split stops on scaled entries:** With two contracts, one can use a tighter SL and the other a wider structural SL.
51. **Channel mid-line early stop:** In channels, a break of the equidistant median can be an early stop before the far rail.
52. **Overnight safety:** Before rollover, add ~20 points to SL to absorb temporary spread widening.
53. **Shooting-star short stop:** Place sell stop ~10 points above the shooting-star upper wick extreme.
54. **Demand-zone long stop:** For longs, place SL under the demand zone that fully absorbed the last sell wave.
55. **Manual invalidate on clear opposite pattern:** Flatten if a clear H1 head-and-shoulders (or equivalent) forms against the position.
