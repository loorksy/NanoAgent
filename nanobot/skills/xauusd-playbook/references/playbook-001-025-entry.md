# Playbook P-001 … P-025 — Flexible entries and timing

Grep `P-0(0[1-9]|1[0-9]|2[0-5])`.

### P-001 — Beyond classic support and resistance
- **Kind:** INTERPRETIVE
- **Judgment:** Do not require a horizontal S/R touch. In strong gold trends, reactions often come from dynamic trendlines or mid-range liquidity gaps.

### P-002 — Immediate entry when the story is complete
- **Kind:** INTERPRETIVE
- **Judgment:** If buy/sell conditions and the liquidity sweep are already done, prefer a now-valid marketable plan. Waiting for an extra dip can miss the move. Rec path still does not auto-send; execution stays HITL.

### P-003 — Distance vs target paradox
- **Kind:** INTERPRETIVE (RR floor is DETERMINISTIC G8)
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
- **Kind:** DETERMINISTIC — `live().IDEA_STALE_HOURS` / pending TTL (G14 uses the stricter pending TTL)
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
- **Judgment:** If the H1 is a decisive break, prefer the decision near the close of that hour rather than the first minute of the next (spread/slippage). Not a session lock; G15 owns clock bans.

### P-022 — Fast EMA as dynamic entry in trends
- **Kind:** INTERPRETIVE
- **Judgment:** In strong trends, a bounce from a fast EMA (e.g. 20) is enough. Do not demand a prior swing low.

### P-023 — Fade an exhausted ADR day
- **Kind:** INTERPRETIVE (200% ADR chase ban is DETERMINISTIC news 82)
- **Judgment:** If gold has already stretched far beyond a normal day's range, a first rejection candle can justify a mean-reversion idea. Do not chase the stretch.

### P-024 — Split entries
- **Kind:** INTERPRETIVE
- **Judgment:** Two-slice entry (now + a pending a small offset) beats all-or-nothing. Size still sums to G20 risk.

### P-025 — Broken high that flips to support
- **Kind:** INTERPRETIVE
- **Judgment:** Role reversal is valid only if the bounce is fast with a clear rejection bar — not a slow grind into the level.
