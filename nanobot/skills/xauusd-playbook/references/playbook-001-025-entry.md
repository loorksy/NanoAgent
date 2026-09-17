# Playbook P-001 … P-025 — Flexible entries and timing

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-001 … P-025 | `playbook-001-025-entry.md` | P-012 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl` | P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008, P-009, P-010, P-011, P-013, P-014, P-015, P-016, P-017, P-018, P-019, P-020, P-021, P-022, P-023, P-024, P-025 |

## Contents

- [P-001 — Beyond classic support and resistance](#p-001-beyond-classic-support-and-resistance)
- [P-002 — Immediate entry when the story is complete](#p-002-immediate-entry-when-the-story-is-complete)
- [P-003 — Distance vs target paradox](#p-003-distance-vs-target-paradox)
- [P-004 — Front-run explosive closes](#p-004-front-run-explosive-closes)
- [P-005 — Incomplete bounce (front-running the level)](#p-005-incomplete-bounce-front-running-the-level)
- [P-006 — Enter from FVG, not the broken high](#p-006-enter-from-fvg-not-the-broken-high)
- [P-007 — Counter engulfing as enough](#p-007-counter-engulfing-as-enough)
- [P-008 — Session-open range break](#p-008-session-open-range-break)
- [P-009 — Equilibrium entries](#p-009-equilibrium-entries)
- [P-010 — Two-timeframe timing](#p-010-two-timeframe-timing)
- [P-011 — Trendline fan, steepest first](#p-011-trendline-fan-steepest-first)
- [P-012 — Cancel stale conditional entries](#p-012-cancel-stale-conditional-entries)
- [P-013 — News-candle tail as support](#p-013-news-candle-tail-as-support)
- [P-014 — Absorption as entry](#p-014-absorption-as-entry)
- [P-015 — Break of the small counter-trendline](#p-015-break-of-the-small-counter-trendline)
- [P-016 — Do not wait for a deep pullback in a steep trend](#p-016-do-not-wait-for-a-deep-pullback-in-a-steep-trend)
- [P-017 — Round-number reactions](#p-017-round-number-reactions)
- [P-018 — Failed bear pattern becomes a long](#p-018-failed-bear-pattern-becomes-a-long)
- [P-019 — Three white soldiers after a box](#p-019-three-white-soldiers-after-a-box)
- [P-020 — Range reclaim](#p-020-range-reclaim)
- [P-021 — Hourly close timing](#p-021-hourly-close-timing)
- [P-022 — Fast EMA as dynamic entry in trends](#p-022-fast-ema-as-dynamic-entry-in-trends)
- [P-023 — Fade an exhausted ADR day](#p-023-fade-an-exhausted-adr-day)
- [P-024 — Split entries](#p-024-split-entries)
- [P-025 — Broken high that flips to support](#p-025-broken-high-that-flips-to-support)


Grep `P-0(0[1-9]|1[0-9]|2[0-5])`.

### P-001 — Beyond classic support and resistance
- **Kind:** INTERPRETIVE
- **Judgment:** Do not require a horizontal S/R touch. In strong gold trends, reactions often come from dynamic trendlines or mid-range liquidity gaps.

### P-002 — Immediate entry when the story is complete
- **Kind:** INTERPRETIVE
- **Judgment:** If buy/sell conditions and the liquidity sweep are already done, prefer a now-valid marketable plan. Waiting for an extra dip can miss the move. Rec path still does not auto-send; execution stays HITL.

### P-003 — Distance vs target paradox
- **Kind:** INTERPRETIVE (reward-to-risk floor is DETERMINISTIC)
- **Judgment:** If the wait-for-pullback is as large as the whole target, the idea is incoherent. Prefer momentum continuation or stand aside.

### P-004 — Front-run explosive closes
- **Kind:** INTERPRETIVE
- **Judgment:** On gold impulse bars, waiting for the close can consume most of the expected range. Allow anticipatory entries when H1 path agrees. Do not pretend an unclosed M1 is a BOS.

### P-005 — Incomplete bounce (front-running the level)
- **Kind:** INTERPRETIVE
- **Judgment:** Institutions often rest orders before the posted S/R. Allow an entry window that starts before the obvious line. Exact point offsets are not a second gate — use ATR/structure.

### P-006 — Enter from FVG, not the broken high
- **Kind:** INTERPRETIVE
- **Judgment:** In an uptrend, gold often turns from the first fair-value gap above the broken high instead of returning to tag the high.

### P-007 — Counter engulfing as enough
- **Kind:** INTERPRETIVE
- **Judgment:** Slow reds then a strong green that eats two prior bodies is a valid long without a support tag.

### P-008 — Session-open range break
- **Kind:** INTERPRETIVE
- **Judgment:** At London or New York open, a sharp Asia-range break is a momentum entry. Do not demand a retest in the first impulse.

### P-009 — Equilibrium entries
- **Kind:** INTERPRETIVE
- **Judgment:** On large impulses, 50% of the wave is a preferred entry even with no prior swing.

### P-010 — Two-timeframe timing
- **Kind:** INTERPRETIVE
- **Judgment:** M15 reversal vs H1 mid-impulse: priority is the H1 path. Do not fade H1 with a cute M15 pattern.

### P-011 — Trendline fan, steepest first
- **Kind:** INTERPRETIVE
- **Judgment:** When gold accelerates, enter off the steepest inner line, not the sleepy outer line.

### P-012 — Cancel stale conditional entries
- **Kind:** DETERMINISTIC — `live().IDEA_STALE_HOURS` / pending TTL (pending-order validity uses the stricter pending TTL)
- **Judgment:** If price has not reached the conditional zone within the live stale window, cancel. Probability has flipped toward a break rather than a bounce.

### P-013 — News-candle tail as support
- **Kind:** INTERPRETIVE (news freeze is DETERMINISTIC)
- **Judgment:** After the void/blackout, the news bar's tail is a zone. Enter on a tag of that tail, not on "yesterday's low."

### P-014 — Absorption as entry
- **Kind:** INTERPRETIVE
- **Judgment:** Repeated lower wicks in a tight box are a long without drawn lines.

### P-015 — Break of the small counter-trendline
- **Kind:** INTERPRETIVE
- **Judgment:** In a pullback, breaking the minor descending line is enough to join the higher-timeframe uptrend.

### P-016 — Do not wait for a deep pullback in a steep trend
- **Kind:** INTERPRETIVE
- **Judgment:** When the rise is near-vertical, waiting for a deep dip misses the rally. Use shallow flags or stand aside — do not invent a 38% must-touch.

### P-017 — Round-number reactions
- **Kind:** INTERPRETIVE
- **Judgment:** Big figures can act as entries if a rejection candle prints there, even without prior structure. Stops still go on odd prints, not the figure (P-032).

### P-018 — Failed bear pattern becomes a long
- **Kind:** INTERPRETIVE
- **Judgment:** A double top that cannot push down and then breaks the neckline upward is an immediate contrary long.

### P-019 — Three white soldiers after a box
- **Kind:** INTERPRETIVE
- **Judgment:** Three rising bodies with expanding tick volume after a range is enough. Oscillators are optional.

### P-020 — Range reclaim
- **Kind:** INTERPRETIVE
- **Judgment:** Drop under support then close back above on the same bar is an immediate reclaim long.

### P-021 — Hourly close timing
- **Kind:** INTERPRETIVE
- **Judgment:** If the H1 is a decisive break, prefer the decision near the close of that hour rather than the first minute of the next (spread/slippage). Not a session lock; session and calendar lock owns clock bans.

### P-022 — Fast EMA as dynamic entry in trends
- **Kind:** INTERPRETIVE
- **Judgment:** In strong trends, a bounce from a fast EMA (e.g. 20) is enough. Do not demand a prior swing low.

### P-023 — Fade an exhausted ADR day
- **Kind:** INTERPRETIVE (200% ADR chase ban is DETERMINISTIC news 82)
- **Judgment:** If gold has already stretched far beyond a normal day's range, a first rejection candle can justify a mean-reversion idea. Do not chase the stretch.

### P-024 — Split entries
- **Kind:** INTERPRETIVE
- **Judgment:** Two-slice entry (now + a pending a small offset) beats all-or-nothing. Size still sums to position sizing risk.

### P-025 — Broken high that flips to support
- **Kind:** INTERPRETIVE
- **Judgment:** Role reversal is valid only if the bounce is fast with a clear rejection bar — not a slow grind into the level.
