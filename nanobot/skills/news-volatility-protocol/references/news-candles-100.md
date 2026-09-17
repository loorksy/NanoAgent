# News-candle encyclopedia C-001 … C-100

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| C-001 … C-100 | `news-candles-100.md` | C-016 → `nanobot/trading/gates/news_candle.py::evaluate_news_candle_shield`<br>C-017 → `nanobot/trading/gates/news_candle.py::is_news_candle`<br>C-018 → `nanobot/trading/gates/news_candle.py::is_news_candle`<br>C-031 → `nanobot/trading/gates/news_candle.py::is_news_candle`<br>C-046 → `nanobot/trading/gates/spread_guard.py::evaluate_spread_guard`<br>C-050 → `nanobot/trading/gates/slippage_guard.py::evaluate_slippage_guard`<br>C-056 → `nanobot/trading/gates/spread_guard.py::evaluate_spread_guard`<br>C-093 → `nanobot/trading/gates/adr_gap.py::evaluate_gap_chase`<br>C-100 → `nanobot/trading/gates/news_candle.py::evaluate_news_candle_shield` | C-001, C-002, C-003, C-004, C-005, C-006, C-007, C-008, C-009, C-010, C-011, C-012, C-013, C-014, C-015, C-019, C-020, C-021, C-022, C-023, C-024, C-025, C-026, C-027, C-028, C-029, C-030, C-032, C-033, C-034, C-035, C-036, C-037, C-038, C-039, C-040, C-041, C-042, C-043, C-044, C-045, C-047, C-048, C-049, C-051, C-052, C-053, C-054, C-055, C-057, C-058, C-059, C-060, C-061, C-062, C-063, C-064, C-065, C-066, C-067, C-068, C-069, C-070, C-071, C-072, C-073, C-074, C-075, C-076, C-077, C-078, C-079, C-080, C-081, C-082, C-083, C-084, C-085, C-086, C-087, C-088, C-089, C-090, C-091, C-092, C-094, C-095, C-096, C-097, C-098, C-099 |

## Contents

- [C-001 — US 8:30 / 10:00](#c-001-us-830--1000)
- [C-002 — :45 flash PMI](#c-002-45-flash-pmi)
- [C-003 — FOMC 14:00 ET](#c-003-fomc-1400-et)
- [C-004 — Presser 14:30 ET](#c-004-presser-1430-et)
- [C-005 — NFP first Friday 8:30 ET](#c-005-nfp-first-friday-830-et)
- [C-006 — London open UK data](#c-006-london-open-uk-data)
- [C-007 — London PM gold fix](#c-007-london-pm-gold-fix)
- [C-008 — Treasury auctions 13:00 ET](#c-008-treasury-auctions-1300-et)
- [C-009 — OpEx / futures expiry Friday](#c-009-opex--futures-expiry-friday)
- [C-010 — API sync < 60s](#c-010-api-sync--60s)
- [C-011 — EIA / oil 10:30 ET Wednesday](#c-011-eia--oil-1030-et-wednesday)
- [C-012 — ECB Thursday 14:15 CET](#c-012-ecb-thursday-1415-cet)
- [C-013 — OPEC](#c-013-opec)
- [C-014 — Unscheduled chair TV](#c-014-unscheduled-chair-tv)
- [C-015 — Quarter-end last 30 minutes](#c-015-quarter-end-last-30-minutes)
- [C-016 — 3× ATR](#c-016-3-atr)
- [C-017 — M1 range outlier](#c-017-m1-range-outlier)
- [C-018 — M5 vs ADR](#c-018-m5-vs-adr)
- [C-019 — Velocity](#c-019-velocity)
- [C-020 — Current bar = last ten combined](#c-020-current-bar--last-ten-combined)
- [C-021 — Hidden gap inside the bar](#c-021-hidden-gap-inside-the-bar)
- [C-022 — >3.5σ Bollinger close](#c-022-35-bollinger-close)
- [C-023 — One H1 eats three days](#c-023-one-h1-eats-three-days)
- [C-024 — Spike then freeze](#c-024-spike-then-freeze)
- [C-025 — Expanding 1x-2x-4x M5s](#c-025-expanding-1x-2x-4x-m5s)
- [C-026 — Coil then giant](#c-026-coil-then-giant)
- [C-027 — PDH and PDL in one M15](#c-027-pdh-and-pdl-in-one-m15)
- [C-028 — Full-body 120+ point M5 marubozu](#c-028-full-body-120-point-m5-marubozu)
- [C-029 — 80% give-back in the same bar](#c-029-80-give-back-in-the-same-bar)
- [C-030 — Range z-score > 4](#c-030-range-z-score--4)
- [C-031 — Tick-volume z > 3.5](#c-031-tick-volume-z--35)
- [C-032 — Tick frequency spike](#c-032-tick-frequency-spike)
- [C-033 — Front-loaded climax](#c-033-front-loaded-climax)
- [C-034 — M1 volume = quiet H1](#c-034-m1-volume--quiet-h1)
- [C-035 — No 5ms gaps between ticks](#c-035-no-5ms-gaps-between-ticks)
- [C-036 — Buy volume at the low of a red spike](#c-036-buy-volume-at-the-low-of-a-red-spike)
- [C-037 — One bar = 25% of the session](#c-037-one-bar--25-of-the-session)
- [C-038 — Price up, next bars' volume down](#c-038-price-up-next-bars-volume-down)
- [C-039 — Session max ticks at a break](#c-039-session-max-ticks-at-a-break)
- [C-040 — 90% one-sided delta](#c-040-90-one-sided-delta)
- [C-041 — Ask evaporation](#c-041-ask-evaporation)
- [C-042 — Same-minute vs history](#c-042-same-minute-vs-history)
- [C-043 — Ticks piled on the wick](#c-043-ticks-piled-on-the-wick)
- [C-044 — Two-second freeze then 200 ticks](#c-044-two-second-freeze-then-200-ticks)
- [C-045 — Huge slip on low ticks](#c-045-huge-slip-on-low-ticks)
- [C-046 — Spread > 3× normal](#c-046-spread--3-normal)
- [C-047 — Pumping spread](#c-047-pumping-spread)
- [C-048 — Wide spread into a green rocket](#c-048-wide-spread-into-a-green-rocket)
- [C-049 — Bid/ask freeze asymmetry](#c-049-bidask-freeze-asymmetry)
- [C-050 — Probe slippage](#c-050-probe-slippage)
- [C-051 — DOM cleared](#c-051-dom-cleared)
- [C-052 — Spread widens 10s before price](#c-052-spread-widens-10s-before-price)
- [C-053 — Gap ticks](#c-053-gap-ticks)
- [C-054 — Mid-NY spread blowout](#c-054-mid-ny-spread-blowout)
- [C-055 — Spread-wick trap at resistance](#c-055-spread-wick-trap-at-resistance)
- [C-056 — Spread stays wide 3+ minutes](#c-056-spread-stays-wide-3-minutes)
- [C-057 — Gold spread vs EURUSD](#c-057-gold-spread-vs-eurusd)
- [C-058 — Ask-only ATH](#c-058-ask-only-ath)
- [C-059 — Straight-line vacuum dump](#c-059-straight-line-vacuum-dump)
- [C-060 — Wide spread, tiny range, before a speech](#c-060-wide-spread-tiny-range-before-a-speech)
- [C-061 — DXY mirror](#c-061-dxy-mirror)
- [C-062 — US10Y shock](#c-062-us10y-shock)
- [C-063 — Silver 95% sync](#c-063-silver-95-sync)
- [C-064 — Decoupling rocket](#c-064-decoupling-rocket)
- [C-065 — Risk-off ES dump](#c-065-risk-off-es-dump)
- [C-066 — Brent sync](#c-066-brent-sync)
- [C-067 — USDJPY flash](#c-067-usdjpy-flash)
- [C-068 — Copper split](#c-068-copper-split)
- [C-069 — VIX +5%](#c-069-vix-5)
- [C-070 — CHF/JPY haven stack](#c-070-chfjpy-haven-stack)
- [C-071 — FX intervention](#c-071-fx-intervention)
- [C-072 — Crypto dump, gold up](#c-072-crypto-dump-gold-up)
- [C-073 — XAUEUR confirms](#c-073-xaueur-confirms)
- [C-074 — TIPS breakdown](#c-074-tips-breakdown)
- [C-075 — EURUSD leads by 10s](#c-075-eurusd-leads-by-10s)
- [C-076 — Expanding horn](#c-076-expanding-horn)
- [C-077 — Engulfing flush](#c-077-engulfing-flush)
- [C-078 — Exhaustion pin](#c-078-exhaustion-pin)
- [C-079 — Shadowless run](#c-079-shadowless-run)
- [C-080 — Tower / imbalance](#c-080-tower--imbalance)
- [C-081 — Outside-bar vs last five](#c-081-outside-bar-vs-last-five)
- [C-082 — V-reversal pair](#c-082-v-reversal-pair)
- [C-083 — Full close beyond resistance, no upper wick](#c-083-full-close-beyond-resistance-no-upper-wick)
- [C-084 — Three same-size M5s](#c-084-three-same-size-m5s)
- [C-085 — One bar breaks slant + flat + fib](#c-085-one-bar-breaks-slant--flat--fib)
- [C-086 — Super-sized doji](#c-086-super-sized-doji)
- [C-087 — Fake hang then collapse](#c-087-fake-hang-then-collapse)
- [C-088 — Intraday breakaway gap](#c-088-intraday-breakaway-gap)
- [C-089 — Asia range eaten at NY open](#c-089-asia-range-eaten-at-ny-open)
- [C-090 — H4 marubozu from stacked news](#c-090-h4-marubozu-from-stacked-news)
- [C-091 — Asian midnight flash](#c-091-asian-midnight-flash)
- [C-092 — CME halt shadow](#c-092-cme-halt-shadow)
- [C-093 — Weekend gap candle](#c-093-weekend-gap-candle)
- [C-094 — Strike / strait headline bar](#c-094-strike--strait-headline-bar)
- [C-095 — Silent coil then 80-point bar, empty calendar](#c-095-silent-coil-then-80-point-bar-empty-calendar)
- [C-096 — Tariffs / sanctions bar](#c-096-tariffs--sanctions-bar)
- [C-097 — Regional-bank panic buy](#c-097-regional-bank-panic-buy)
- [C-098 — De-escalation dump bar](#c-098-de-escalation-dump-bar)
- [C-099 — US downgrade bar](#c-099-us-downgrade-bar)
- [C-100 — Triple print = certain news candle](#c-100-triple-print--certain-news-candle)


Grep `C-0[0-9][0-9]` or `C-100`. TOC: calendar time 1–15 · range/ATR 16–30 · tick volume 31–45 · spread 46–60 · intermarket 61–75 · morphology 76–90 · unscheduled 91–100.

A candle is a **news candle** when several families agree. C-016, C-031, and C-046 together are enough even with an empty calendar (C-100). Numeric z-scores and ATR multiples are DETERMINISTIC (`NEWS_CANDLE_*` in `policy.live()`).

## Time and calendar (C-001 … C-015)

### C-001 — US 8:30 / 10:00
- **Kind:** INTERPRETIVE time signature
- **Judgment:** A wide bar starting on those US minutes with a red calendar is a news candle immediately.

### C-002 — :45 flash PMI
- **Kind:** INTERPRETIVE
- **Judgment:** Explosive bars at minute 45 (e.g. 9:45 NY) are usually flash PMI.

### C-003 — FOMC 14:00 ET
- **Kind:** INTERPRETIVE
- **Judgment:** The 2:00 PM ET bar on FOMC day is a rate-decision candle regardless of shape.

### C-004 — Presser 14:30 ET
- **Kind:** INTERPRETIVE
- **Judgment:** Sequential bars from 2:30 ET for ~45 minutes are live Q&A candles, not one print.

### C-005 — NFP first Friday 8:30 ET
- **Kind:** INTERPRETIVE
- **Judgment:** That bar is NFP. Do not wait for a pattern name.

### C-006 — London open UK data
- **Kind:** INTERPRETIVE
- **Judgment:** 08:00–08:15 London with UK GDP/CPI is a European macro candle.

### C-007 — London PM gold fix
- **Kind:** INTERPRETIVE
- **Judgment:** 15:00 London high-volume bars are often the PM fix, not "random."

### C-008 — Treasury auctions 13:00 ET
- **Kind:** INTERPRETIVE
- **Judgment:** Explosive 1:00 PM ET bars often map to 10Y/30Y auction results.

### C-009 — OpEx / futures expiry Friday
- **Kind:** INTERPRETIVE
- **Judgment:** Last-Friday-of-month wildness is inventory, still treat as a shock candle for risk.

### C-010 — API sync < 60s
- **Kind:** INTERPRETIVE (news and event shield uses calendar timestamps)
- **Judgment:** If the bar's open is within a minute of a high-impact timestamp, label it news.

### C-011 — EIA / oil 10:30 ET Wednesday
- **Kind:** INTERPRETIVE
- **Judgment:** If gold explodes with crude at that stamp, record an energy-linked news candle.

### C-012 — ECB Thursday 14:15 CET
- **Kind:** INTERPRETIVE
- **Judgment:** Meeting days: that bar is a monetary shock that bleeds into gold.

### C-013 — OPEC
- **Kind:** INTERPRETIVE
- **Judgment:** Unclocked production headlines on OPEC days are commodity news candles.

### C-014 — Unscheduled chair TV
- **Kind:** INTERPRETIVE + FEATURE-03/05
- **Judgment:** A bar that starts with a live Powell/Lagarde clip is a news candle.

### C-015 — Quarter-end last 30 minutes
- **Kind:** INTERPRETIVE
- **Judgment:** Mar/Jun/Sep/Dec last half-hour oddities are rebalance candles.

## Range and ATR (C-016 … C-030)

### C-016 — 3× ATR
- **Kind:** DETERMINISTIC — `NEWS_CANDLE_ATR_MULT`
- **Judgment:** High−low greater than live ATR multiple of the 14-bar ATR → news candle.

### C-017 — M1 range outlier
- **Kind:** DETERMINISTIC — `NEWS_CANDLE_M1_POINTS`
- **Judgment:** M1 range beyond the live point floor outside a dead session is a news fingerprint.

### C-018 — M5 vs ADR
- **Kind:** DETERMINISTIC — `NEWS_CANDLE_M5_ADR_FRACTION`
- **Judgment:** One M5 that eats the live fraction of ADR is a news candle.

### C-019 — Velocity
- **Kind:** INTERPRETIVE
- **Judgment:** Sustained travel of >1.5 points/sec for ~30s without a pause is shock flow.

### C-020 — Current bar = last ten combined
- **Kind:** INTERPRETIVE
- **Judgment:** If this bar's range ≈ sum of the prior ten, the driver is external.

### C-021 — Hidden gap inside the bar
- **Kind:** INTERPRETIVE (bad tick bad-tick filter)
- **Judgment:** Tick-to-tick holes inside the bar are news or a bad tick. If it snaps back, bad-tick filter; if it holds, news.

### C-022 — >3.5σ Bollinger close
- **Kind:** INTERPRETIVE
- **Judgment:** Close outside 3.5 sigma is a shock event.

### C-023 — One H1 eats three days
- **Kind:** INTERPRETIVE
- **Judgment:** An H1 that swallows three prior daily ranges is a news candle.

### C-024 — Spike then freeze
- **Kind:** INTERPRETIVE
- **Judgment:** >100 points in <120s then a sudden stall on a figure is a spike news bar.

### C-025 — Expanding 1x-2x-4x M5s
- **Kind:** INTERPRETIVE
- **Judgment:** Geometric expansion of M5 ranges in a few minutes is news, not a random trend.

### C-026 — Coil then giant
- **Kind:** INTERPRETIVE
- **Judgment:** A giant after a 15-point box is a news insertion into dead tape.

### C-027 — PDH and PDL in one M15
- **Kind:** INTERPRETIVE
- **Judgment:** Taking yesterday's high **and** low inside one M15 is a data shock.

### C-028 — Full-body 120+ point M5 marubozu
- **Kind:** INTERPRETIVE using live point math
- **Judgment:** Almost no wicks and a huge M5 body is institutional news flow.

### C-029 — 80% give-back in the same bar
- **Kind:** INTERPRETIVE
- **Judgment:** Huge travel then an 80% retrace in the same bar is a two-sided news purge.

### C-030 — Range z-score > 4
- **Kind:** INTERPRETIVE (volume z is DETERMINISTIC C-031)
- **Judgment:** Session range z above four is statistical news.

## Tick velocity and volume (C-031 … C-045)

### C-031 — Tick-volume z > 3.5
- **Kind:** DETERMINISTIC — `NEWS_CANDLE_VOLUME_Z`
- **Judgment:** Tick count z vs the last 50 bars beyond live z is a news candle.

### C-032 — Tick frequency spike
- **Kind:** INTERPRETIVE
- **Judgment:** 5–15 ticks/sec jumping to 80–150 is a fingerprint.

### C-033 — Front-loaded climax
- **Kind:** INTERPRETIVE
- **Judgment:** ~70% of the bar's ticks in the first 15 seconds then silence is a print.

### C-034 — M1 volume = quiet H1
- **Kind:** INTERPRETIVE
- **Judgment:** One M1 matching a calm H1's ticks is ultra-news.

### C-035 — No 5ms gaps between ticks
- **Kind:** INTERPRETIVE
- **Judgment:** Saturated tick stream is algo news, not a human tape.

### C-036 — Buy volume at the low of a red spike
- **Kind:** INTERPRETIVE
- **Judgment:** Heavy buy ticks at the bottom of a news dump is absorption.

### C-037 — One bar = 25% of the session
- **Kind:** INTERPRETIVE
- **Judgment:** A single bar owning a quarter of session activity is news.

### C-038 — Price up, next bars' volume down
- **Kind:** INTERPRETIVE
- **Judgment:** Rocket without follow-through volume is a one-shot news pop.

### C-039 — Session max ticks at a break
- **Kind:** INTERPRETIVE
- **Judgment:** Day's peak ticks exactly as a level breaks on data is confirmatory.

### C-040 — 90% one-sided delta
- **Kind:** INTERPRETIVE
- **Judgment:** One side owns almost all ticks: news imbalance.

### C-041 — Ask evaporation
- **Kind:** INTERPRETIVE
- **Judgment:** Offers pulled, wide upticks: makers stepped aside for a print.

### C-042 — Same-minute vs history
- **Kind:** INTERPRETIVE
- **Judgment:** This minute's volume 5× the same minute on prior days is news.

### C-043 — Ticks piled on the wick
- **Kind:** INTERPRETIVE
- **Judgment:** Dense ticks only on the extreme wick is a stop-run print.

### C-044 — Two-second freeze then 200 ticks
- **Kind:** INTERPRETIVE
- **Judgment:** Broker queue pause then a burst is a news processing stall.

### C-045 — Huge slip on low ticks
- **Kind:** INTERPRETIVE
- **Judgment:** Vacuum slip with few ticks: empty book at the number.

## Spread (C-046 … C-060)

### C-046 — Spread > 3× normal
- **Kind:** DETERMINISTIC overlap with spread guard / pre-news multiplier
- **Judgment:** Instant 3× (or live cap) bid/ask is a news fingerprint.

### C-047 — Pumping spread
- **Kind:** INTERPRETIVE
- **Judgment:** Spread inflating and shrinking every tick is maker protection.

### C-048 — Wide spread into a green rocket
- **Kind:** INTERPRETIVE
- **Judgment:** Price up while spread stays huge: no stable offer.

### C-049 — Bid/ask freeze asymmetry
- **Kind:** INTERPRETIVE
- **Judgment:** Ask frozen, bid leaping (or inverse) is a shock book.

### C-050 — Probe slippage
- **Kind:** DETERMINISTIC — `SLIPPAGE_PROBE_POINTS`
- **Judgment:** A probe fill worse than live probe points is news-quality slip.

### C-051 — DOM cleared
- **Kind:** INTERPRETIVE
- **Judgment:** Depth vanishes; tiny lots move price: news vacuum.

### C-052 — Spread widens 10s before price
- **Kind:** INTERPRETIVE
- **Judgment:** Makers knew. Treat as a news candle even before the spike.

### C-053 — Gap ticks
- **Kind:** INTERPRETIVE
- **Judgment:** 2450.10 → 2451.80 in one tick with no mids is news or bad tick.

### C-054 — Mid-NY spread blowout
- **Kind:** INTERPRETIVE
- **Judgment:** Spread exploding in peak NY liquidity is unscheduled news.

### C-055 — Spread-wick trap at resistance
- **Kind:** INTERPRETIVE
- **Judgment:** Spread doubles into a high then price dumps: maker stop hunt.

### C-056 — Spread stays wide 3+ minutes
- **Kind:** DETERMINISTIC overlap with `SPREAD_STABLE_SECONDS`
- **Judgment:** If spread never calms, the panic is still on. spread guard stays veto.

### C-057 — Gold spread vs EURUSD
- **Kind:** INTERPRETIVE
- **Judgment:** Gold 5× wide while EURUSD is normal: metal/geo, not a broad FX print.

### C-058 — Ask-only ATH
- **Kind:** INTERPRETIVE
- **Judgment:** Ask tags ATH, bid never does: short-covering print, not a real break.

### C-059 — Straight-line vacuum dump
- **Kind:** INTERPRETIVE
- **Judgment:** No opposing bids, a linear drop: liquidity vacuum news.

### C-060 — Wide spread, tiny range, before a speech
- **Kind:** INTERPRETIVE
- **Judgment:** Makers widened, price has not run yet — the chair is about to talk.

## Intermarket (C-061 … C-075)

### C-061 — DXY mirror
- **Kind:** INTERPRETIVE + FEATURE-10
- **Judgment:** Gold rocket vs dollar dump in the same second is a data candle.

### C-062 — US10Y shock
- **Kind:** INTERPRETIVE
- **Judgment:** 10-year yield jumping >1.5% of its level as gold spikes is a bond-news candle.

### C-063 — Silver 95% sync
- **Kind:** INTERPRETIVE
- **Judgment:** XAU and XAG identical in the same minute is a metals news candle.

### C-064 — Decoupling rocket
- **Kind:** INTERPRETIVE
- **Judgment:** Gold **and** DXY both vertical: war or bank panic (absolute haven).

### C-065 — Risk-off ES dump
- **Kind:** INTERPRETIVE
- **Judgment:** S&P giant red with gold giant green: risk-off shock candle.

### C-066 — Brent sync
- **Kind:** INTERPRETIVE
- **Judgment:** Gold and Brent exploding together: Middle-East/supply geopolitics.

### C-067 — USDJPY flash
- **Kind:** INTERPRETIVE
- **Judgment:** USDJPY 80 points with gold: shared US data (CPI/NFP).

### C-068 — Copper split
- **Kind:** INTERPRETIVE
- **Judgment:** Gold alone, copper flat → rates story. Gold+copper → PMI/growth story.

### C-069 — VIX +5%
- **Kind:** INTERPRETIVE
- **Judgment:** VIX jumping hard with gold is a fear candle.

### C-070 — CHF/JPY haven stack
- **Kind:** INTERPRETIVE
- **Judgment:** Gold up with CHF and JPY vs the complex: haven news.

### C-071 — FX intervention
- **Kind:** INTERPRETIVE
- **Judgment:** Record moves in gold-linked FX from a visible BOJ/etc intervention: treat gold bar as news.

### C-072 — Crypto dump, gold up
- **Kind:** INTERPRETIVE
- **Judgment:** BTC liquidity fleeing into gold is a risk-off news candle.

### C-073 — XAUEUR confirms
- **Kind:** INTERPRETIVE
- **Judgment:** New highs in both XAUUSD and XAUEUR: not "just a weak dollar."

### C-074 — TIPS breakdown
- **Kind:** INTERPRETIVE
- **Judgment:** Real yields collapsing into a CPI print feeds a historic gold buy bar.

### C-075 — EURUSD leads by 10s
- **Kind:** INTERPRETIVE
- **Judgment:** EURUSD explosion 10 seconds first is an early warning the gold news bar is next.

## Morphology (C-076 … C-090)

### C-076 — Expanding horn
- **Kind:** INTERPRETIVE
- **Judgment:** Long both wicks, tiny body: two-sided news.

### C-077 — Engulfing flush
- **Kind:** INTERPRETIVE
- **Judgment:** Break prior high then close beyond prior low in the same TF: news purge.

### C-078 — Exhaustion pin
- **Kind:** INTERPRETIVE
- **Judgment:** Wick >80% of a 150+ point bar: classic news rejection.

### C-079 — Shadowless run
- **Kind:** INTERPRETIVE
- **Judgment:** M1/M5 with no wicks: one-way institutional news.

### C-080 — Tower / imbalance
- **Kind:** INTERPRETIVE
- **Judgment:** A vertical bar through many zones leaving a full imbalance: news tower.

### C-081 — Outside-bar vs last five
- **Kind:** INTERPRETIVE
- **Judgment:** Range beyond the last five highs **and** lows: news outside bar.

### C-082 — V-reversal pair
- **Kind:** INTERPRETIVE
- **Judgment:** −80 M1 then +100 next M1: stop-run then the real news path.

### C-083 — Full close beyond resistance, no upper wick
- **Kind:** INTERPRETIVE
- **Judgment:** M15 fully above a hard roof without an upper wick: news thrust.

### C-084 — Three same-size M5s
- **Kind:** INTERPRETIVE
- **Judgment:** Three consecutive almost-identical impulse M5s almost only happen after major data.

### C-085 — One bar breaks slant + flat + fib
- **Kind:** INTERPRETIVE
- **Judgment:** A single bar killing three maps is a news bar.

### C-086 — Super-sized doji
- **Kind:** INTERPRETIVE
- **Judgment:** 200-point range, open≈close: war inside the print.

### C-087 — Fake hang then collapse
- **Kind:** INTERPRETIVE
- **Judgment:** New high then last-10-second collapse leaving a giant upper wick: news fake-out.

### C-088 — Intraday breakaway gap
- **Kind:** INTERPRETIVE
- **Judgment:** Next M1 opens a gap vs prior close in a live session: news gap.

### C-089 — Asia range eaten at NY open
- **Kind:** INTERPRETIVE
- **Judgment:** One NY-open bar eats the whole Tokyo box: news or NY data.

### C-090 — H4 marubozu from stacked news
- **Kind:** INTERPRETIVE
- **Judgment:** A full H4 marubozu from a sequence of agreeing prints is a regime bar.

## Unscheduled (C-091 … C-100)

### C-091 — Asian midnight flash
- **Kind:** INTERPRETIVE
- **Judgment:** >100 points in dead Asia is military/speech until proven otherwise.

### C-092 — CME halt shadow
- **Kind:** INTERPRETIVE
- **Judgment:** Tick freeze then a leap: futures circuit breaker. Treat as news.

### C-093 — Weekend gap candle
- **Kind:** DETERMINISTIC overlap with N-090
- **Judgment:** Monday open gap beyond live points is a weekend-news candle.

### C-094 — Strike / strait headline bar
- **Kind:** INTERPRETIVE + FEATURE-05
- **Judgment:** Vertical green on attack/shipping headlines with record buy ticks.

### C-095 — Silent coil then 80-point bar, empty calendar
- **Kind:** INTERPRETIVE
- **Judgment:** That is a wire headline. Run regex emergency.

### C-096 — Tariffs / sanctions bar
- **Kind:** INTERPRETIVE
- **Judgment:** Sudden duty/sanction headlines that move metals: news candle.

### C-097 — Regional-bank panic buy
- **Kind:** INTERPRETIVE
- **Judgment:** Bank-stock collapse generating a gold panic-buy bar.

### C-098 — De-escalation dump bar
- **Kind:** INTERPRETIVE
- **Judgment:** Official calm → giant red gold bar. Invalidates N-087 longs.

### C-099 — US downgrade bar
- **Kind:** INTERPRETIVE
- **Judgment:** Sovereign rating cut → gold ignition bar.

### C-100 — Triple print = certain news candle
- **Kind:** DETERMINISTIC combo — ATR multiple + volume z + spread blowout
- **Judgment:** If live ATR, tick-volume z, and spread all trip, label **news candle** and run the news shield whether or not the calendar is red.
