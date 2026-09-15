---
name: gold-news-volatility
description: XAUUSD news and violent-volatility operating rules (1-100). Use for pre-news freezes, reading CPI/NFP/FOMC shocks, news-candle microstructure, spread/slippage safety, post-news trend riding, and geopolitical safe-haven protocols.
---

# Gold News and Volatility Rules (1-100)

## Section 1 — Pre-news precautions (1-18)

1. **Pre-news freeze window:** Ban new entries 15 minutes before high-impact releases (CPI, NFP, FOMC).
2. **Cancel all pendings:** Delete limit/stop pendings 10 minutes before the event to avoid catastrophic slippage fills.
3. **Protect winners:** Move open winners to BE or close ~70% size 10 minutes before pivotal data.
4. **Flatten near-entry trades:** Close any trade still within ~30 gold points of entry to avoid instant stop-out from spread blowouts.
5. **Pre-emptive spread watch:** Two minutes before release, if spread is >3× normal, engage auto trade lock.
6. **Priced-in analysis:** Compare the prior 4 hours of price vs consensus — a sharp pre-move often means the outcome is already absorbed.
7. **Pre-news range box:** Mark high/low of the last 30 minutes before the print as sweep boundaries.
8. **Disable tight trailing:** Turn off tight trailing immediately before news — initial chaos will stop you out of the real trend.
9. **Simultaneous prints risk:** Escalate danger when two red events print together (e.g. unemployment + NFP).
10. **Ping check:** If MetaAPI/MT5 latency >50ms one minute before news, ban trading.
11. **Avoid rollover collisions:** Ban entries if the event collides with daily swap/rollover.
12. **Consensus deviation threshold:** Require a minimum surprise delta (e.g. ~50k NFP jobs) before treating the print as tradable shock.
13. **Fed testimony silence:** Stay fully flat for the entire chair testimony and press Q&A.
14. **DXY pre-leak:** If DXY breaks lows minutes before the print with no visible cause, treat as early leak favoring gold upside.
15. **Macro extreme rails:** Prefetch nearest daily S/R 150–300 points away as likely wick magnets.
16. **Half risk on data days:** Cap risk at 0.5% (vs 1%) for any trade taken the same day as major data.
17. **No stop-market chase:** Never place buy-stop/sell-stop to catch the explosion — fills at worst slippage.
18. **Scheduled vs unscheduled split:** Code paths must distinguish calendar events from sudden geopolitics.

## Section 2 — Reading the live print (19-34)

19. **CPI logic:** Hotter-than-expected CPI → yields/USD up → sharp gold dump (inverse when cooler).
20. **NFP dynamics:** Very strong jobs + falling unemployment → delayed cuts → immediate gold sell pressure.
21. **Split-data paralysis:** Strong jobs but soft wages → classify as conflicted high-risk and cancel all trades.
22. **Revisions matter:** A downside revision to last month can erase a “good” headline and flip gold bullish.
23. **Decision vs presser:** The rate decision sets the first move; the chair’s tone ~30 minutes later often sets the day trend.
24. **Buy rumor, sell fact:** If gold rallied hard into a 99% priced cut, the actual print often dumps as profit-taking.
25. **Surprise delta score:** Exact consensus matches usually mean chop — do not force a directional trade.
26. **PMI < 50:** Sub-50 PMI contraction impulse often lifts gold as a hedge.
27. **Ignore secondary noise:** Drop consumer confidence / home sales when they land in the same week as CPI/NFP.
28. **Yield divergence:** USD-positive headline but falling 10Y yields → gold dip is likely temporary.
29. **PPI as CPI preview:** Hot PPI often seeds gradual gold downside into the next CPI.
30. **Absorption speed:** If a bad print is absorbed back to release price in <5 minutes, institutional bid is dominant.
31. **Jobless claims spikes:** Unusual claims jumps support tactical gold longs.
32. **Dovish keyword buy:** Phrases like slowdown, downside risks, watch employment → tactical long bias.
33. **FedWatch jump:** Post-print spike in cut odds supports gold continuation for the session.
34. **USD+gold both down:** Simultaneous dumps mean broad de-leveraging, not a clean data response.

## Section 3 — News candle microstructure (35-55)

35. **60-second void:** Absolute ban on entries/analysis in the first 60 seconds — algorithmic chaos.
36. **Two-sided liquidity sweep:** A candle that tags pre-news high then low in the same minute is a flush, not a trend.
37. **First M5 close is reference:** Trade in the direction of the first post-news M5 body if body ≥70% of range.
38. **Rejection wick rule:** Upper wick ≥2× body after a spike up = trap → arm short.
39. **News FVG:** Giant one-minute voids become later magnets — do not buy until ~50% fill.
40. **True break needs M15 close:** Direction counts only after an M15 fully closes outside the pre-news box.
41. **Instant engulf reverse:** +100 in minute one fully engulfed in minute two → day bias is down.
42. **No FOMO mid-giant bar:** After a 150-point bar, ban chasing the extreme — enter only on pullback.
43. **Tick volume climax:** Volume collapsing right after the first burst means fuel is spent.
44. **Range reclaim reversal:** Break of a major daily low then reclaim within 10 minutes = short trap / major long.
45. **Wickless cascade:** Successive one-way minutes with no wicks = sustained institutional flow — ride it.
46. **Asia high fake:** News wick through Asia high by a few points then collapse is a textbook daily sweep.
47. **M1 noise filter:** Do not make fatal decisions on M1 closes after news — use M5/M15.
48. **Bollinger > extreme:** ~90% of the bar outside upper band implies mandatory mean reversion toward mid.
49. **Shock wick as future SL:** The extreme wick of the shock candle is the ideal later stop anchor.
50. **Trendline break confirmation:** If the shock closes above a major H1 descending trendline, bias flips sustainably up.
51. **Volatility compression trap:** If gold barely moves (~20 points) on a huge print, a delayed violent expansion often hits within 30 minutes.
52. **Hollow break:** Fast support break on weak tick volume is a fake — do not sell it.
53. **News doji stalemate:** First M15 as a huge-volume doji = war draw — wait for a side break.
54. **First micro LL warning:** In a spike up, breaking the prior one-minute low is the first profit-taking warning.
55. **Hold above shock high:** Holding above the first shock high for >15 minutes supports continuation to new extremes.

## Section 4 — Spread, slippage, operational safety (56-72)

56. **Spread kill switch:** Halt execution if gold spread >60 points (60 cents); resume only after 3 minutes of normal spread.
57. **Slippage tolerance:** Reject market sends if expected slippage >25 points.
58. **No martingale under volatility:** Ban add-ons/doubling during post-news violence.
59. **Execution latency:** If order round-trip >1000ms in the journal, cancel further entry attempts.
60. **Prefer offset limits after news:** Post-news entries use calculated buy/sell limits, not naked market chases.
61. **Intraday equity guard:** If floating equity drops 2% in one news candle, flatten everything.
62. **Post-stop cooldown:** After a news stop-out, mandatory 45-minute cool-off before scanning again.
63. **Wide buffer SL after calm:** Post-stabilization entries need ≥+30 points extra SL buffer for late wicks.
64. **Avoid :58–:02 around news hours:** Skip new orders across the hour boundary during event windows.
65. **Half-distance pending cancel:** If price runs 50% to TP before fill, delete the pending forever.
66. **Bad tick shield:** Ignore a tick that spikes ~80 points and snaps back on the next tick.
67. **Volatility-adjusted lots:** If ATR doubles, cut lot size roughly in half.
68. **No blind fade:** Ban buying “because it fell a lot” or selling “because it rose a lot” without a completed pattern.
69. **Windfall protocol:** If the full day target prints within 2 minutes of the release, close 100% and stop trading.
70. **Margin level warning:** Ban new risk if margin level falls below 500% in high vol.
71. **Disconnect alert:** If feed drops >10 seconds with an open news trade, emergency-alert the operator.
72. **SL-first packet:** Send stop loss in the same atomic packet as entry — never naked.

## Section 5 — Riding the real post-news trend (73-86)

73. **15-minute rule:** Best high-odds entries usually begin 15–30 minutes after the print.
74. **Retest shock high/low:** Wait for a calm retest of the break level, then enter with the rebound/continuation.
75. **First H1 close after data:** Day bias often equals the first post-event H1 close direction.
76. **OTE pullback:** After the first explosion, Fib the full impulse and enter 61.8–78.6.
77. **NY continuation window:** If 15:30 Makkah data confirms direction, trend often persists until ~18:30.
78. **Staged exits after majors:** Split TP into three clips to ride extended data trends.
79. **Weekly level break → swing:** Data break + hold above a prior weekly high can justify multi-day swing longs.
80. **Absorption detection:** Failure to print a new high in the next three bars after the shock warns of reverse/correction.
81. **Engulf after pullback:** After the shock pullback, an M5 engulfing of corrective bars arms continuation.
82. **ADR overextension:** At ~200% ADR on the news move, ban chase; hunt reversals instead.
83. **Broken roof becomes floor:** Any ceiling detonated by news becomes the best buy-on-dip later.
84. **DXY must confirm gold longs:** Do not buy gold post-news unless DXY keeps breaking its micro lows (except geopolitics).
85. **Broadening wedge exit:** Higher highs + lower lows after news = chaotic expansion — flatten.
86. **Follow-up official comments:** Post-data Fed speak that affirms the print holds the trend; contradictory speak can reverse it.

## Section 6 — Geopolitical safe haven (87-100)

87. **Cancel technicals in hot war:** On sudden airstrikes/war breaks, ignore resistance and oscillators — priority is long.
88. **No shorting panic:** Absolute ban on gold shorts during escalating geopolitical attacks regardless of TA bait.
89. **Trusted flash → market buy:** On confirmed major geo flash from reputable wires, market-buy without waiting for a dip.
90. **Weekend gap caution:** Gap-up >150 points on Monday from weekend events — ban immediate chase; wait for gap digest.
91. **Full decoupling allowed:** In global panic, gold can rise with USD and falling equities — do not require weak USD.
92. **Open extension targets:** In geo panic, cancel near TPs; use outer Fib extensions 2.0 / 2.618.
93. **De-escalation invalidation:** Official ceasefire/de-escalation → flatten longs immediately ahead of violent dumps.
94. **Banking panic dips are buys:** Regional bank failures / sovereign stress — every dip is a buy.
95. **Announcement candle stop:** Place SL ~20 points under the low of the candle that launched on the geo flash.
96. **Media amplification trap:** Distinguish skirmishes from major crises; hype of minor events often dumps hours later.
97. **Mainstream FOMO peak:** When non-traders’ TV leads with gold mania, the rally is late — raise caution.
98. **News velocity metric:** Escalation headlines every few minutes keep the long light green.
99. **Chokepoint / oil shocks:** Threats to shipping lanes that lift oil also lift gold — strategic long bias.
100. **Sovereign volatility rule:** In panic, the smart trader is not the one who catches every tick — it is the one who exits the storm with capital intact.
