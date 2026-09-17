# News protocol N-001 … N-100

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| N-001 … N-100 | `news-100.md` | N-001 → `nanobot/trading/gates/news_window.py::evaluate_news_window`<br>N-002 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl`<br>N-003 → `nanobot/trading/gates/news_operational.py::evaluate_news_operational`<br>N-004 → `nanobot/trading/gates/news_operational.py::evaluate_news_operational`<br>N-005 → `nanobot/trading/gates/spread_guard.py::evaluate_spread_guard`<br>N-010 → `nanobot/trading/gates/stale_quote.py::evaluate_stale_quote`<br>N-011 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>N-016 → `nanobot/trading/gates/position_sizing.py::evaluate_position_sizing`<br>N-035 → `nanobot/trading/gates/news_operational.py::evaluate_news_operational`<br>N-056 → `nanobot/trading/gates/spread_guard.py::evaluate_spread_guard`<br>N-057 → `nanobot/trading/gates/slippage_guard.py::evaluate_slippage_guard`<br>N-059 → `nanobot/trading/gates/slippage_guard.py::evaluate_slippage_guard`<br>N-061 → `nanobot/trading/gates/drawdown_breaker.py::evaluate_drawdown_breaker`<br>N-062 → `nanobot/trading/gates/cooldown_lock.py::evaluate_cooldown_lock`<br>N-063 → `nanobot/trading/gates/trade_management.py::management_snapshot`<br>N-064 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>N-065 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl`<br>N-066 → `nanobot/trading/gates/bad_tick.py::evaluate_bad_tick`<br>N-067 → `nanobot/trading/gates/position_sizing.py::lot_from_balance`<br>N-070 → `nanobot/trading/gates/margin_guard.py::evaluate_margin_guard`<br>N-071 → `nanobot/trading/gates/stale_quote.py::evaluate_stale_quote`<br>N-073 → `nanobot/trading/gates/news_operational.py::evaluate_news_operational`<br>N-082 → `nanobot/trading/gates/adr_gap.py::evaluate_adr_chase`<br>N-090 → `nanobot/trading/gates/adr_gap.py::evaluate_gap_chase` | N-006, N-007, N-008, N-009, N-012, N-013, N-014, N-015, N-017, N-018, N-019, N-020, N-021, N-022, N-023, N-024, N-025, N-026, N-027, N-028, N-029, N-030, N-031, N-032, N-033, N-034, N-036, N-037, N-038, N-039, N-040, N-041, N-042, N-043, N-044, N-045, N-046, N-047, N-048, N-049, N-050, N-051, N-052, N-053, N-054, N-055, N-058, N-060, N-068, N-069, N-072, N-074, N-075, N-076, N-077, N-078, N-079, N-080, N-081, N-083, N-084, N-085, N-086, N-087, N-088, N-089, N-091, N-092, N-093, N-094, N-095, N-096, N-097, N-098, N-099, N-100 |

## Contents

- [N-001 — Pre-news freeze](#n-001-pre-news-freeze)
- [N-002 — Cancel pendings](#n-002-cancel-pendings)
- [N-003 — Protect open winners](#n-003-protect-open-winners)
- [N-004 — Flatten near-entry trades](#n-004-flatten-near-entry-trades)
- [N-005 — Pre-emptive spread blowout](#n-005-pre-emptive-spread-blowout)
- [N-006 — Priced-in tape](#n-006-priced-in-tape)
- [N-007 — Map the pre-news box](#n-007-map-the-pre-news-box)
- [N-008 — Disable tight trails into the print](#n-008-disable-tight-trails-into-the-print)
- [N-009 — Stacked releases](#n-009-stacked-releases)
- [N-010 — Ping check](#n-010-ping-check)
- [N-011 — No entries on rollover-news overlap](#n-011-no-entries-on-rollover-news-overlap)
- [N-012 — Surprise threshold](#n-012-surprise-threshold)
- [N-013 — Chair testimony day](#n-013-chair-testimony-day)
- [N-014 — DXY leak before the print](#n-014-dxy-leak-before-the-print)
- [N-015 — Map 150–300-point shelves](#n-015-map-150300-point-shelves)
- [N-016 — Half risk on red-folder days](#n-016-half-risk-on-red-folder-days)
- [N-017 — No stop-market through the print](#n-017-no-stop-market-through-the-print)
- [N-018 — Scheduled vs unscheduled](#n-018-scheduled-vs-unscheduled)
- [N-019 — CPI logic](#n-019-cpi-logic)
- [N-020 — NFP logic](#n-020-nfp-logic)
- [N-021 — Split data](#n-021-split-data)
- [N-022 — Revisions](#n-022-revisions)
- [N-023 — Decision vs presser](#n-023-decision-vs-presser)
- [N-024 — Buy rumor, sell fact](#n-024-buy-rumor-sell-fact)
- [N-025 — Zero surprise](#n-025-zero-surprise)
- [N-026 — PMI below 50](#n-026-pmi-below-50)
- [N-027 — Ignore second-tier on CPI week](#n-027-ignore-second-tier-on-cpi-week)
- [N-028 — Yields disagree with the dollar](#n-028-yields-disagree-with-the-dollar)
- [N-029 — PPI as CPI preview](#n-029-ppi-as-cpi-preview)
- [N-030 — Absorption speed](#n-030-absorption-speed)
- [N-031 — Jobless claims spikes](#n-031-jobless-claims-spikes)
- [N-032 — Dovish keywords](#n-032-dovish-keywords)
- [N-033 — FedWatch jump](#n-033-fedwatch-jump)
- [N-034 — Gold down with the dollar](#n-034-gold-down-with-the-dollar)
- [N-035 — 60-second void](#n-035-60-second-void)
- [N-036 — Two-sided sweep bar](#n-036-two-sided-sweep-bar)
- [N-037 — First M5 body as the map](#n-037-first-m5-body-as-the-map)
- [N-038 — Rejection-wick rule](#n-038-rejection-wick-rule)
- [N-039 — News FVG](#n-039-news-fvg)
- [N-040 — True break of the pre-news box](#n-040-true-break-of-the-pre-news-box)
- [N-041 — Immediate engulf of the spike](#n-041-immediate-engulf-of-the-spike)
- [N-042 — No FOMO mid-bar](#n-042-no-fomo-mid-bar)
- [N-043 — Tick-volume climax then death](#n-043-tick-volume-climax-then-death)
- [N-044 — Range reclaim after a sweep](#n-044-range-reclaim-after-a-sweep)
- [N-045 — No-wick follow-through](#n-045-no-wick-follow-through)
- [N-046 — Asia high fake on the print](#n-046-asia-high-fake-on-the-print)
- [N-047 — M1 is noise](#n-047-m1-is-noise)
- [N-048 — Bollinger stretch](#n-048-bollinger-stretch)
- [N-049 — News-bar tail is the later stop](#n-049-news-bar-tail-is-the-later-stop)
- [N-050 — H1 trendline break on the print](#n-050-h1-trendline-break-on-the-print)
- [N-051 — Compression trap](#n-051-compression-trap)
- [N-052 — Empty-volume support break](#n-052-empty-volume-support-break)
- [N-053 — Giant news doji](#n-053-giant-news-doji)
- [N-054 — First lower-low after a spike](#n-054-first-lower-low-after-a-spike)
- [N-055 — Hold above the news high](#n-055-hold-above-the-news-high)
- [N-056 — Spread kill](#n-056-spread-kill)
- [N-057 — Slippage cap](#n-057-slippage-cap)
- [N-058 — No martingale in the storm](#n-058-no-martingale-in-the-storm)
- [N-059 — Broker latency](#n-059-broker-latency)
- [N-060 — Limits after the print, not markets](#n-060-limits-after-the-print-not-markets)
- [N-061 — Intraday equity spike](#n-061-intraday-equity-spike)
- [N-062 — Cool-down after a news stop](#n-062-cool-down-after-a-news-stop)
- [N-063 — Wider post-news stops](#n-063-wider-post-news-stops)
- [N-064 — Minute 58–02 during news](#n-064-minute-5802-during-news)
- [N-065 — Half-distance cancel](#n-065-half-distance-cancel)
- [N-066 — Bad tick](#n-066-bad-tick)
- [N-067 — ATR-adjusted lots](#n-067-atr-adjusted-lots)
- [N-068 — No blind fade of a shock](#n-068-no-blind-fade-of-a-shock)
- [N-069 — Windfall flatten](#n-069-windfall-flatten)
- [N-070 — Margin floor](#n-070-margin-floor)
- [N-071 — Disconnect during a print](#n-071-disconnect-during-a-print)
- [N-072 — SL in the same packet as entry](#n-072-sl-in-the-same-packet-as-entry)
- [N-073 — 15-minute rule](#n-073-15-minute-rule)
- [N-074 — Retest of the shock high/low](#n-074-retest-of-the-shock-highlow)
- [N-075 — First H1 close after the print](#n-075-first-h1-close-after-the-print)
- [N-076 — OTE of the shock bar](#n-076-ote-of-the-shock-bar)
- [N-077 — NY continuation window](#n-077-ny-continuation-window)
- [N-078 — Scale out of news trends](#n-078-scale-out-of-news-trends)
- [N-079 — Weekly break + news = swing](#n-079-weekly-break--news--swing)
- [N-080 — No new high after the shock](#n-080-no-new-high-after-the-shock)
- [N-081 — Engulf of the pullback](#n-081-engulf-of-the-pullback)
- [N-082 — 200% ADR — no chase](#n-082-200-adr--no-chase)
- [N-083 — Broken roof becomes the buy](#n-083-broken-roof-becomes-the-buy)
- [N-084 — DXY must agree for gold longs](#n-084-dxy-must-agree-for-gold-longs)
- [N-085 — Broadening wedge after news](#n-085-broadening-wedge-after-news)
- [N-086 — Post-data Fed speak](#n-086-post-data-fed-speak)
- [N-087 — Wars cancel technical shorts](#n-087-wars-cancel-technical-shorts)
- [N-088 — No shorting panic](#n-088-no-shorting-panic)
- [N-089 — First confirmed headline long](#n-089-first-confirmed-headline-long)
- [N-090 — Weekend gap-up, do not chase](#n-090-weekend-gap-up-do-not-chase)
- [N-091 — Decouple from dollar and equities](#n-091-decouple-from-dollar-and-equities)
- [N-092 — Open extension targets](#n-092-open-extension-targets)
- [N-093 — De-escalation invalidates](#n-093-de-escalation-invalidates)
- [N-094 — Bank-failure dip buys](#n-094-bank-failure-dip-buys)
- [N-095 — Stop under the announcement bar](#n-095-stop-under-the-announcement-bar)
- [N-096 — Media amplification trap](#n-096-media-amplification-trap)
- [N-097 — When non-traders buy gold on TV](#n-097-when-non-traders-buy-gold-on-tv)
- [N-098 — News velocity](#n-098-news-velocity)
- [N-099 — Straits and oil](#n-099-straits-and-oil)
- [N-100 — Survive the storm](#n-100-survive-the-storm)


Grep `N-0[0-9][0-9]` or `N-100`. TOC: pre-print 1–18 · reading the print 19–34 · news-candle microstructure 35–55 · operational safety 56–72 · post-print trend 73–86 · geopolitics 87–100.

## Pre-print (N-001 … N-018)

### N-001 — Pre-news freeze
- **Kind:** DETERMINISTIC — news and event shield blackout is stricter than this 15-minute rule (`NEWS_BLACKOUT_BEFORE_MINUTES`)
- **Judgment:** No new recommendations inside the live freeze before CPI/NFP/FOMC.

### N-002 — Cancel pendings
- **Kind:** DETERMINISTIC — news operational freeze / `NEWS_SHIELD_MINUTES`
- **Judgment:** Delete working gold pendings inside the live shield window so they cannot fill on slippage.

### N-003 — Protect open winners
- **Kind:** DETERMINISTIC overlap with news operational freeze
- **Judgment:** BE or harvest most size inside the shield window. Do not "ride CPI."

### N-004 — Flatten near-entry trades
- **Kind:** DETERMINISTIC — `FLAT_NEAR_ENTRY_POINTS`
- **Judgment:** If an open is still inside the live near-entry distance, close it before the print.

### N-005 — Pre-emptive spread blowout
- **Kind:** DETERMINISTIC — `SPREAD_MULTIPLIER_PRE_NEWS` / `SPREAD_PRE_NEWS_MINUTES`
- **Judgment:** If spread is already a multiple of normal just before the print, lock trading.

### N-006 — Priced-in tape
- **Kind:** INTERPRETIVE
- **Judgment:** A one-way grind in the four hours before the print often means the number is already in. Fade the "obvious" first tick.

### N-007 — Map the pre-news box
- **Kind:** INTERPRETIVE
- **Judgment:** Draw the last-half-hour high/low. Those rails become the sweep magnet (N-036, N-040).

### N-008 — Disable tight trails into the print
- **Kind:** INTERPRETIVE
- **Judgment:** The first noise will stop a tight trail and steal the real trend.

### N-009 — Stacked releases
- **Kind:** INTERPRETIVE
- **Judgment:** Two reds at once (NFP + unemployment) raise the moment to "conflicted." Prefer no plan.

### N-010 — Ping check
- **Kind:** DETERMINISTIC — `PING_MAX_MS`
- **Judgment:** If broker ping exceeds live max, ban execution.

### N-011 — No entries on rollover-news overlap
- **Kind:** DETERMINISTIC — session and calendar lock rollover + news
- **Judgment:** If the print lands on daily contract rollover, stay out.

### N-012 — Surprise threshold
- **Kind:** INTERPRETIVE
- **Judgment:** Tiny beats do not trend. Need a meaningful miss/beat (jobs tens of thousands, CPI in tenths) before calling a shock.

### N-013 — Chair testimony day
- **Kind:** INTERPRETIVE (calendar still drives news and event shield)
- **Judgment:** Stay silent through the full testimony and Q&A, not just the first minute.

### N-014 — DXY leak before the print
- **Kind:** INTERPRETIVE
- **Judgment:** Dollar breaking lows for no chart reason minutes before a print is often a leak — gold-bullish until the number disagrees.

### N-015 — Map 150–300-point shelves
- **Kind:** INTERPRETIVE
- **Judgment:** Pre-draw daily S/R a news wick might tag. Those are later targets, not entries during the void.

### N-016 — Half risk on red-folder days
- **Kind:** DETERMINISTIC — `RISK_PCT_NEWS_DAY` / position sizing
- **Judgment:** Same-day entries after the window use live news-day risk, not full risk.

### N-017 — No stop-market through the print
- **Kind:** INTERPRETIVE (slippage slippage and latency)
- **Judgment:** Ban buy-stop/sell-stop intended to catch the explosion. They fill at the worst tick.

### N-018 — Scheduled vs unscheduled
- **Kind:** INTERPRETIVE
- **Judgment:** Calendar prints use freeze/void. Geopolitics uses FEATURE-05 and N-087+ immediately.

## Reading the print (N-019 … N-034)

### N-019 — CPI logic
- **Kind:** INTERPRETIVE
- **Judgment:** Hot CPI → yields and dollar up → gold down hard, and the inverse.

### N-020 — NFP logic
- **Kind:** INTERPRETIVE
- **Judgment:** Hot jobs + falling unemployment → delayed cuts → immediate gold sell.

### N-021 — Split data
- **Kind:** INTERPRETIVE
- **Judgment:** Jobs dollar-positive and wages dollar-negative: conflicted. Cancel plans.

### N-022 — Revisions
- **Kind:** INTERPRETIVE
- **Judgment:** A downward revision can erase a "good" print and flip gold up.

### N-023 — Decision vs presser
- **Kind:** INTERPRETIVE
- **Judgment:** The rate decision starts the first move; the chair 30 minutes later often sets the day.

### N-024 — Buy rumor, sell fact
- **Kind:** INTERPRETIVE
- **Judgment:** If gold already ripped on a 99% cut, the actual cut is often a dump.

### N-025 — Zero surprise
- **Kind:** INTERPRETIVE
- **Judgment:** Print = forecast → chop, not a trend. Do not force a side.

### N-026 — PMI below 50
- **Kind:** INTERPRETIVE
- **Judgment:** Contraction PMI is a gold-positive growth scare.

### N-027 — Ignore second-tier on CPI week
- **Kind:** INTERPRETIVE
- **Judgment:** Consumer confidence / home sales on CPI week are noise.

### N-028 — Yields disagree with the dollar
- **Kind:** INTERPRETIVE
- **Judgment:** Dollar-positive print but 10-year yields drop: gold dip is likely temporary.

### N-029 — PPI as CPI preview
- **Kind:** INTERPRETIVE
- **Judgment:** Hot PPI often pre-sells gold into CPI week.

### N-030 — Absorption speed
- **Kind:** INTERPRETIVE
- **Judgment:** If a "bad" print is fully absorbed in a few minutes, institutions are buying. Respect that.

### N-031 — Jobless claims spikes
- **Kind:** INTERPRETIVE
- **Judgment:** Unusual claims jumps support tactical gold longs.

### N-032 — Dovish keywords
- **Kind:** INTERPRETIVE + FEATURE-05/09
- **Judgment:** Slowdown, downside risks, watching jobs → tactical longs. Hawkish inverse.

### N-033 — FedWatch jump
- **Kind:** INTERPRETIVE
- **Judgment:** A post-print jump in cut odds supports gold for the rest of the session.

### N-034 — Gold down with the dollar
- **Kind:** INTERPRETIVE
- **Judgment:** Both falling is a liquidity flush, not a textbook data response.

## Microstructure (N-035 … N-055)

### N-035 — 60-second void
- **Kind:** DETERMINISTIC — `NEWS_VOID_SECONDS` / news operational freeze
- **Judgment:** No entries, no "the trend is in" calls in the first live void.

### N-036 — Two-sided sweep bar
- **Kind:** INTERPRETIVE
- **Judgment:** Wick both pre-news high and low in one minute is a purge, not a trend.

### N-037 — First M5 body as the map
- **Kind:** INTERPRETIVE
- **Judgment:** After the void, the first M5 close: if the body owns most of the range, that direction is the working map.

### N-038 — Rejection-wick rule
- **Kind:** INTERPRETIVE
- **Judgment:** A news bar with an upper wick twice the body after a spike is a trap — look short after freeze.

### N-039 — News FVG
- **Kind:** INTERPRETIVE
- **Judgment:** Do not buy until price returns a meaningful fraction of the minute-gap left by the print.

### N-040 — True break of the pre-news box
- **Kind:** INTERPRETIVE
- **Judgment:** Count the trend only if M15 fully closes outside the pre-news rails.

### N-041 — Immediate engulf of the spike
- **Kind:** INTERPRETIVE
- **Judgment:** +100 then a next-minute bar that eats it: the day is likely down.

### N-042 — No FOMO mid-bar
- **Kind:** INTERPRETIVE (ADR chase DETERMINISTIC)
- **Judgment:** If the bar already traveled a huge distance, ban buying the high. Enter only on a pullback after freeze.

### N-043 — Tick-volume climax then death
- **Kind:** INTERPRETIVE
- **Judgment:** If volume dies right after the first bar, the fuel is gone.

### N-044 — Range reclaim after a sweep
- **Kind:** INTERPRETIVE
- **Judgment:** News takes a daily low then trades back above within minutes: sell trap, major long — after freeze.

### N-045 — No-wick follow-through
- **Kind:** INTERPRETIVE
- **Judgment:** One-color minutes without wicks is institutional flow. Ride, do not fade.

### N-046 — Asia high fake on the print
- **Kind:** INTERPRETIVE
- **Judgment:** News tags Asia high by a few points then dumps: classic daily sweep.

### N-047 — M1 is noise
- **Kind:** INTERPRETIVE
- **Judgment:** Do not make life decisions on M1 closes in news. Use M5/M15.

### N-048 — Bollinger stretch
- **Kind:** INTERPRETIVE
- **Judgment:** News bar mostly outside the outer band is an extreme; expect a midline snap.

### N-049 — News-bar tail is the later stop
- **Kind:** INTERPRETIVE
- **Judgment:** The extreme of the shock bar is the invalidation for the later continuation trade.

### N-050 — H1 trendline break on the print
- **Kind:** INTERPRETIVE
- **Judgment:** If the explosion also closes H1 through a major slant, regime can change for the session.

### N-051 — Compression trap
- **Kind:** INTERPRETIVE
- **Judgment:** A red print that barely moves is a coiled spring. A late explosion is likely.

### N-052 — Empty-volume support break
- **Kind:** INTERPRETIVE
- **Judgment:** A fast low-tick break of support in a vacuum is fake.

### N-053 — Giant news doji
- **Kind:** INTERPRETIVE
- **Judgment:** First M15 as a huge-volume doji is a stalemate. Trade the later rail break only.

### N-054 — First lower-low after a spike
- **Kind:** INTERPRETIVE
- **Judgment:** In a spike-up, losing the prior M1 low is the first profit-taking alarm.

### N-055 — Hold above the news high
- **Kind:** INTERPRETIVE
- **Judgment:** If gold holds the first shock high for a full quarter-hour, continuation toward new extremes is in play.

## Operational safety (N-056 … N-072)

### N-056 — Spread kill
- **Kind:** DETERMINISTIC — spread guard / `SPREAD_MAX_POINTS` / `SPREAD_STABLE_SECONDS`
- **Judgment:** Engine off above live spread cap until spread is stable for the live seconds.

### N-057 — Slippage cap
- **Kind:** DETERMINISTIC — slippage and latency / `SLIPPAGE_MAX_POINTS`
- **Judgment:** Reject marketable sends if expected slippage exceeds live cap.

### N-058 — No martingale in the storm
- **Kind:** INTERPRETIVE
- **Judgment:** Ban averaging a loser during post-news violence.

### N-059 — Broker latency
- **Kind:** DETERMINISTIC — `EXEC_LATENCY_MAX_MS`
- **Judgment:** If journal processing exceeds live latency, abort sends.

### N-060 — Limits after the print, not markets
- **Kind:** INTERPRETIVE
- **Judgment:** Post-news entries prefer calculated limits over panic markets.

### N-061 — Intraday equity spike
- **Kind:** DETERMINISTIC — `EQUITY_SPIKE_PCT`
- **Judgment:** If floating equity drops the live percent in one bar, flatten path.

### N-062 — Cool-down after a news stop
- **Kind:** DETERMINISTIC — `COOLDOWN_AFTER_NEWS_STOP_MINUTES` / cooldown lock
- **Judgment:** After a news-window stop-out, sit out the live minutes.

### N-063 — Wider post-news stops
- **Kind:** DETERMINISTIC — `POST_NEWS_SL_BUFFER_POINTS`
- **Judgment:** After the tape calms, add the live extra stop air against leftover tails.

### N-064 — Minute 58–02 during news
- **Kind:** DETERMINISTIC — session and calendar lock rollover minutes, only with news/high-impact nearby
- **Judgment:** Do not send in the live rollover minute window when news is active.

### N-065 — Half-distance cancel
- **Kind:** DETERMINISTIC — same as P-193 / pending-order validity
- **Judgment:** If price already ran half the target before fill, delete the pending.

### N-066 — Bad tick
- **Kind:** DETERMINISTIC — bad-tick filter / `BAD_TICK_POINTS`
- **Judgment:** Ignore a spike-and-snap beyond live distance.

### N-067 — ATR-adjusted lots
- **Kind:** DETERMINISTIC — position sizing / `ATR_DOUBLE_LOT_HALVE`
- **Judgment:** If ATR doubles, halve size.

### N-068 — No blind fade of a shock
- **Kind:** INTERPRETIVE
- **Judgment:** Ban "it fell a lot so buy" without a completed pattern after freeze.

### N-069 — Windfall flatten
- **Kind:** INTERPRETIVE
- **Judgment:** If the day's whole target prints in two minutes, flatten 100% and stop.

### N-070 — Margin floor
- **Kind:** DETERMINISTIC — margin guard / `MARGIN_MIN_PCT`
- **Judgment:** No new risk if margin level is under the live percent.

### N-071 — Disconnect during a print
- **Kind:** DETERMINISTIC — `DISCONNECT_ALERT_SECONDS`
- **Judgment:** Alert the operator; do not pretend you are still managing.

### N-072 — SL in the same packet as entry
- **Kind:** INTERPRETIVE / execution implementation
- **Judgment:** Never send a naked entry. Stop travels with the order.

## Post-print trend (N-073 … N-086)

### N-073 — 15-minute rule
- **Kind:** DETERMINISTIC wait — `POST_NEWS_ENTRY_WAIT_MINUTES` / news and event shield after-window
- **Judgment:** Best entries start after the live post-print wait, not in the void.

### N-074 — Retest of the shock high/low
- **Kind:** INTERPRETIVE
- **Judgment:** The quiet tag of the first news-bar extreme is the continuation entry.

### N-075 — First H1 close after the print
- **Kind:** INTERPRETIVE
- **Judgment:** That H1 close is the honest session bias.

### N-076 — OTE of the shock bar
- **Kind:** INTERPRETIVE
- **Judgment:** Fib the whole news bar; entries live in 61.8–78.6 of that impulse.

### N-077 — NY continuation window
- **Kind:** INTERPRETIVE
- **Judgment:** If NY data confirms, the path often holds into late NY. Trail, do not fade immediately.

### N-078 — Scale out of news trends
- **Kind:** INTERPRETIVE using live partial split
- **Judgment:** Data days trend far. Use three harvests, not one.

### N-079 — Weekly break + news = swing
- **Kind:** INTERPRETIVE
- **Judgment:** A print that also holds a weekly high/low can be a multi-day idea, still one live card.

### N-080 — No new high after the shock
- **Kind:** INTERPRETIVE
- **Judgment:** If the next three bars cannot make a new extreme, absorption/reversal is starting.

### N-081 — Engulf of the pullback
- **Kind:** INTERPRETIVE
- **Judgment:** After the shock pullback, an M5 that eats the pullback bars is the add/entry.

### N-082 — 200% ADR — no chase
- **Kind:** DETERMINISTIC — `ADR_CHASE_PCT`
- **Judgment:** If the print already ran the live ADR multiple, hunt reversal signs, do not chase.

### N-083 — Broken roof becomes the buy
- **Kind:** INTERPRETIVE
- **Judgment:** A level detonated by news is the best later dip-buy.

### N-084 — DXY must agree for gold longs
- **Kind:** INTERPRETIVE (except safe-haven)
- **Judgment:** After data, do not buy gold unless the dollar is still making lower lows — unless N-091 applies.

### N-085 — Broadening wedge after news
- **Kind:** INTERPRETIVE
- **Judgment:** Higher highs and lower lows after a print is chaos. Flat.

### N-086 — Post-data Fed speak
- **Kind:** INTERPRETIVE
- **Judgment:** Officials who back the print lock the trend; officials who fight it can reverse it.

## Geopolitics (N-087 … N-100)

### N-087 — Wars cancel technical shorts
- **Kind:** INTERPRETIVE
- **Judgment:** Air strikes / war: ignore overbought. Gold is a bid.

### N-088 — No shorting panic
- **Kind:** INTERPRETIVE
- **Judgment:** Ban gold shorts into escalating geopolitics no matter how pretty the H1 top.

### N-089 — First confirmed headline long
- **Kind:** INTERPRETIVE
- **Judgment:** After a trusted wire confirms a major event, a marketable long proposal is valid. Still HITL. Do not wait for a dip that never comes.

### N-090 — Weekend gap-up, do not chase
- **Kind:** DETERMINISTIC — `GAP_NO_CHASE_POINTS`
- **Judgment:** Monday gap beyond live points: no chase. Wait for fill or a hold-above-gap structure.

### N-091 — Decouple from dollar and equities
- **Kind:** INTERPRETIVE
- **Judgment:** In global panic gold can rise with DXY and with falling stocks. Drop the inverse-dollar requirement.

### N-092 — Open extension targets
- **Kind:** INTERPRETIVE
- **Judgment:** Panic legs use 2.0 / 2.618 extensions, not nearby shorts' supply.

### N-093 — De-escalation invalidates
- **Kind:** INTERPRETIVE
- **Judgment:** Official ceasefire/calm: flatten panic longs. The dump is fast.

### N-094 — Bank-failure dip buys
- **Kind:** INTERPRETIVE
- **Judgment:** Systemic bank stress: every dip is a long until the backstop is believed.

### N-095 — Stop under the announcement bar
- **Kind:** INTERPRETIVE
- **Judgment:** Invalidation is under the bar that started the geopolitical bid, with air.

### N-096 — Media amplification trap
- **Kind:** INTERPRETIVE
- **Judgment:** Skirmish hyped on TV often dumps hours later. Size down unless FEATURE-05 stays hot.

### N-097 — When non-traders buy gold on TV
- **Kind:** INTERPRETIVE
- **Judgment:** Front-page gold mania is late. Tighten, do not add.

### N-098 — News velocity
- **Kind:** INTERPRETIVE
- **Judgment:** Escalation headlines every few minutes = permission to hold longs. Silence after a spike = caution.

### N-099 — Straits and oil
- **Kind:** INTERPRETIVE
- **Judgment:** Threats to shipping/oil lift inflation and gold together. Strategic bias is long.

### N-100 — Survive the storm
- **Kind:** INTERPRETIVE
- **Judgment:** The smart operator is not the one who banks every tick. It is the one who exits the storm with the account intact.
