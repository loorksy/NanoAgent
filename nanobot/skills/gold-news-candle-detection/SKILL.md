---
name: gold-news-candle-detection
description: Algorithmic rules (1-100) to detect and classify XAUUSD news candles via calendar sync, ATR multiples, tick velocity, spread dynamics, intermarket sync, morphology, and unscheduled geopolitics. Use before applying news-shield protocols.
---

# Gold News Candle Detection Rules (1-100)

When multiple detectors fire (ATR×3 + tick z-score + spread blowout), classify as a definite news candle and engage news-shield protocols whether or not the calendar listed an event.

## Section 1 — Calendar / clock sync (1-15)

1. **US 8:30 / 10:00 ET rule:** Wide-range bars at :00 or :30 synced to major US data windows classify as news candles immediately.
2. **:45 flash PMI:** Explosive bars at minute :45 (e.g. 9:45 ET) tied to flash PMI are news candles.
3. **FOMC 14:00 ET:** Any bar at 14:00 ET on FOMC day is a rate-decision candle regardless of shape.
4. **Presser 14:30 ET:** Sequential bars starting 14:30 ET for ~45 minutes are live speech news candles.
5. **NFP first Friday:** 8:30 ET first Friday is NFP by definition — no TA confirmation required.
6. **London open EU macro:** Giant bars 08:00–08:15 London with UK GDP/CPI classify as EU macro news candles.
7. **London PM gold fix:** High-volume surge near 15:00 London reflects bullion fixing flows.
8. **Treasury auction 13:00 ET:** Explosive bars at US auction times link to 10Y/30Y results.
9. **OpEx / futures expiry Fridays:** Abnormal late-month Friday volatility = liquidation/settlement candles.
10. **API sync <60s:** If candle start vs red calendar event delta <60 seconds → auto news candle.
11. **Oil inventory spillover:** Wednesday ~10:30 ET bars that violently move gold with oil = energy-linked news candle.
12. **ECB decision Thursday:** ECB meeting decision bars (CET schedule) are monetary shock candles affecting gold.
13. **OPEC+ meetings:** Unscheduled production decision spikes classify as commodity news candles.
14. **Unscheduled Fed speech streams:** Bars synced to live Fed principal speeches are news candles.
15. **Quarter-end rebalance:** Final 30 minutes of Mar/Jun/Sep/Dec sessions with abnormal flow = institutional rebalance candles.

## Section 2 — Range / ATR detectors (16-30)

16. **3× ATR rule:** Candle range (H−L) > 3× ATR(14) of same TF → confirmed news candle.
17. **M1 outlier:** Gold moving 60–80+ points in one M1 outside dead sessions is a news fingerprint.
18. **ADR fraction:** One M5 consuming >40% of average daily range → news candle.
19. **Velocity metric:** >~1.5 points/second sustained ~30 seconds without pullback.
20. **vs last 20 bars:** Current bar length ≈ sum of prior 10 bars → external news driver.
21. **Hidden intraday gap:** Tick-to-tick jumps leaving an untraded void inside the bar.
22. **Bollinger > 3.5σ:** Close beyond 3.5σ Bollinger = crushing news event.
23. **Weekly range eat:** One H1 engulfing the prior three days’ full range.
24. **Spike candle:** Vertical >100 points in <120 seconds then abrupt stop on a pivot.
25. **Expanding bar anomaly:** M5 lengths doubling geometrically within minutes.
26. **Low-vol breakout bar:** Giant bar after a ≤15-point coil = news ignition.
27. **PDH+PDL same M15:** Breaking yesterday high and low inside one M15 = major data shock.
28. **Near-marubozu M5:** ≥120-point M5 with almost no wicks.
29. **Air-retrace bar:** Huge travel then ~80% retrace inside the same candle without clean bases.
30. **Range z-score > 4:** Statistical range anomaly vs session history.

## Section 3 — Tick velocity and volume (31-45)

31. **Tick volume z-score > 3.5:** Tick count >3.5σ vs last 50 bars.
32. **Tick frequency spike:** From ~5–15 ticks/s to ~80–150 ticks/s on gold.
33. **Volume climax front-load:** ~70% of the bar’s ticks in the first 15 seconds then sudden drop.
34. **M1 ultra-high volume:** One M1 matching a quiet-session full H1 tick count.
35. **Gapless torrent:** Continuous orders with <5ms gaps between ticks.
36. **Buy volume in giant down bar:** Heavy buy absorption at the lows of a crash bar.
37. **25% of session volume in one bar:** Single candle contributes ≥25% of session activity so far.
38. **Rocket on falling follow-through volume:** Spike then dying volume = news impulse without sustainable liquidity.
39. **ATH break volume peak:** Day’s highest tick reading exactly on a key break driven by data.
40. **Heavy delta imbalance:** One side >90% of ticks in the bar.
41. **Ask evaporation:** Buy ticks with wide jumps as liquidity providers pull offers.
42. **Same-minute historical compare:** Volume >500% vs same minute on prior days → news certainty.
43. **Edge density:** Tick density piled on wick extremes = rapid stop flush battle.
44. **Freeze then burst:** ~2s tick freeze (broker load) then 200-tick burst.
45. **Vacuum slip:** Huge slippage on relatively low ticks because opposing book vanished at the print.

## Section 4 — Spread dynamics (46-60)

46. **Spread > 3× normal:** Bid/ask from ~15–20 to 60–120 points in fractions of a second.
47. **Pumping spread:** Spread expands/contracts wildly tick-to-tick — classic protective LP signature.
48. **Wide spread into a trend up:** Rocketing price while spread stays huge = unstable offers.
49. **Bid/Ask freeze asymmetry:** Ask frozen while Bid keeps jumping (or reverse).
50. **Live slippage >20 points:** Between shown and filled price on probe orders.
51. **DOM clearance:** Depth-of-market levels vanish, leaving a vacuum moved by tiny size.
52. **Spread leads price by ~10s:** Dealers widen before the print before price actually runs.
53. **Gapped ticks:** e.g. 2450.10 → 2451.80 with no intermediate prints.
54. **Mid-NY abnormal spread:** Sudden wide spread in peak NY liquidity = emergency event.
55. **Open-spread rejection:** Resistance touch with doubled spread then snap — stop-raid trap.
56. **Spread stays wide >3 minutes after the bar:** Panic regime continues.
57. **Gold-only spread blowout:** Gold spread ×5 while EURUSD normal → metal/geo specific event.
58. **Ask-only ATH pierce:** Ask tags ATH while Bid never does — engineered short squeeze of stops.
59. **Liquidity vacuum slip:** Straight-line drop with no opposing bids.
60. **Wide spread + low realized vol pre-speech:** Classic minutes before a Fed chair talk.

## Section 5 — Intermarket sync (61-75)

61. **DXY mirror spike:** Violent gold up bar second-synced with equally violent DXY down bar.
62. **US10Y shock:** 10Y yield jumps >~1.5% relative move as the gold bar forms.
63. **XAG synchrony:** Gold and silver bars agree >95% in the same minute.
64. **Decoupling anomaly:** Gold and USD both rocket — war/banking absolute haven.
65. **Risk-off with SPX:** Giant SPX down bar synced with giant gold up bar.
66. **Oil sync:** Gold and Brent explode same minute → Middle East / energy geopolitics fingerprint.
67. **USDJPY flash:** USDJPY ±80 points with the gold bar → shared US data shock.
68. **Copper split test:** Gold alone (copper flat) → rates/monetary; gold+copper together → growth/PMI.
69. **VIX spike:** VIX +5% within minutes synced to the gold bar.
70. **CHF/JPY haven sync:** Gold rising with CHF strength across pairs confirms haven news candle.
71. **Central-bank intervention candles:** Extreme FX moves from direct BOJ/etc intervention spilling to gold.
72. **Crypto risk dump:** BTC dumping while gold rockets → flight from risk to traditional haven.
73. **XAUEUR confirmation:** New highs in both XAUUSD and XAUEUR deny “USD-only” explanation.
74. **TIPS breakdown:** Real yields collapsing on CPI → historic gold buy candle fuel.
75. **FX leads gold by ~10s:** Violent EURUSD move 10 seconds before gold warns the gold news candle is imminent.

## Section 6 — Morphology and structure (76-90)

76. **Expanding horn candle:** Long upper + long lower wick with tiny body — two-way news thrash.
77. **Engulfing flush:** Break prior high by ~30 then close ~50 below prior low in the same bar.
78. **Exhaustion pin-bar:** Wick ≥80% of a ≥150-point range — classic news rejection.
79. **Wickless cascade:** Missing shadows on successive M1/M5 = relentless institutional pressure.
80. **Tower / imbalance candle:** Vertical pierce of multiple zones leaving a full imbalance void.
81. **Outside bar extremum:** Range above prior 5 highs and below prior 5 lows simultaneously.
82. **V-reversal pair:** −80 on one minute then +100 on the next — flush then true path.
83. **Body hold above resistance:** M15 full close above hard resistance with no upper wick = news thrust.
84. **3-bar news cascade:** Three near-equal wickless M5 thrusts — rare except after major data.
85. **Multi-level single-bar break:** One candle breaks descending TL + horizontal + Fib together.
86. **Super-sized doji:** ~200-point range with open≈close — bulls vs bears war on the print.
87. **Fake hang / collapse close:** Spikes a high then collapses in last ~10 seconds into a small red body.
88. **Breakaway tick gap:** Next M1 opens ≥15 points above prior close in live continuous session.
89. **Asia range eaten in one pulse:** One bar consumes the entire Tokyo range in the first NY minute.
90. **H4 marubozu from news chain:** An H4 becomes a full marubozu from a sequence of aligned prints.

## Section 7 — Unscheduled geopolitics (91-100)

91. **Asian midnight flash:** >100-point move in the quietest Asia hours → military/urgent statement.
92. **Volatility halt candle:** CME circuit-breaker pause then huge spot jump after halt.
93. **Weekend gap candle:** Monday open gap >150 points from weekend political shocks.
94. **Strike / chokepoint candle:** Vertical long with record buy ticks on attack or strait-closure headlines.
95. **Silent coil then 80-point blast:** No calendar event — wire flash fingerprint.
96. **Tariff / sanctions candle:** Sudden duty/sanctions packages hitting metals trade.
97. **Banking panic buy:** Regional bank equity crash spawning panic gold buying.
98. **De-escalation dump candle:** Giant red bar on official ceasefire/diplomatic end.
99. **Sovereign downgrade candle:** Gold ignition after major US/sovereign rating cuts.
100. **Master classifier:** If ATR ≥3× and tick volume explodes and spread blows out together → definite news candle; engage news shield/protection immediately whether scheduled or surprise.
