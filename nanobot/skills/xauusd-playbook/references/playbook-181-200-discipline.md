# Playbook P-181 … P-200 — Execution discipline

Grep `P-1(8[1-9]|9[0-9]|200)`.

### P-181 — Standing aside is a trade
- **Kind:** INTERPRETIVE
- **Judgment:** Mixed signals: do not publish. Capital protection is the decision. Analytical side remains BUY or SELL if you must pick; the platform may still refuse.

### P-182 — Zero-hesitation auto-send — EXCLUDED
- **Kind:** EXCLUDED
- **Owner:** HITL propose→confirm is mandatory and not a Risk Parameters toggle
- **Judgment:** Do **not** send orders the instant conditions print. Propose, wait for the operator, re-check live fill. This rule is intentionally not implemented as auto-execution.

### P-183 — Pending TTL
- **Kind:** DETERMINISTIC — `live().PENDING_TTL_HOURS` / pending-order validity
- **Judgment:** Unfilled limits/stops expire with the live TTL. Context died.

### P-184 — No add to a same-side loser
- **Kind:** INTERPRETIVE (max positions is open-position cap)
- **Judgment:** Ban a new gold long while an existing long is still red. That is stacking losses.

### P-185 — Scalp vs swing isolation
- **Kind:** DETERMINISTIC identifiers — `MAGIC_SCALP` / `MAGIC_SWING`
- **Judgment:** Never merge a scalp stop with a swing stop.

### P-186 — Unscheduled 1-minute explosion
- **Kind:** DETERMINISTIC — `EMERGENCY_MOVE_POINTS_PER_MINUTE` plus FEATURE-05
- **Judgment:** If gold rips the live emergency distance in a minute with no calendar print, flatten/protect — leak or war until proven otherwise.

### P-187 — Revenge freeze
- **Kind:** DETERMINISTIC — cooldown lock / consecutive-loss minutes (session cooldown vs consecutive-loss cooldown: code uses the stricter policy)
- **Judgment:** After consecutive losses, no new orders until the live cooldown elapses.

### P-188 — Dual lot check
- **Kind:** DETERMINISTIC — position sizing / `LOT_DUAL_CHECK_*`
- **Judgment:** Compute lot twice. A decimal slip is an account event.

### P-189 — Fresh tick before send
- **Kind:** DETERMINISTIC — live quote freshness / `STALE_QUOTE_SECONDS`
- **Judgment:** If the last tick is older than live stale seconds, abort the send.

### P-190 — Drop the bias when structure dies
- **Kind:** INTERPRETIVE
- **Judgment:** If gold CHoCH against you, cancel the old story. No stubbornness.

### P-191 — Daily max loss
- **Kind:** DETERMINISTIC — drawdown and kill switch / `DAILY_DRAWDOWN_PCT`
- **Judgment:** Hit the live daily loss: stop for the day.

### P-192 — Marketable orders when the break is real
- **Kind:** INTERPRETIVE
- **Judgment:** On a confirmed break bar, prefer marketable fills over a limit that misses the train. Still HITL.

### P-193 — Half-distance pending cancel
- **Kind:** DETERMINISTIC — pending-order validity / `HALF_DISTANCE_FRACTION`
- **Judgment:** If price already ran half way to TP before the pending fills, cancel. Do not chase the return.

### P-194 — Comment the why on the ticket
- **Kind:** INTERPRETIVE
- **Judgment:** Store a short code (`BOS_M15_FVG_Retest`) on the comment for post-mortem.

### P-195 — No new risk into the daily close
- **Kind:** DETERMINISTIC — session and calendar lock / `DAILY_CLOSE_LOCK_MINUTES`
- **Judgment:** Ban fresh entries in the live minutes before daily close (spread + swap).

### P-196 — Live fill reward-to-risk
- **Kind:** DETERMINISTIC — confirm path / `MIN_RR_LIVE_FILL`
- **Judgment:** If the fill would degrade below the live live-fill reward-to-risk, cancel. Recommendation minimum reward-to-risk still uses the farthest-target floor.

### P-197 — Official holidays off
- **Kind:** DETERMINISTIC — session and calendar lock holiday calendar
- **Judgment:** New Year, US Thanksgiving, and similar: algorithms off. Makers are gone.

### P-198 — TF contradiction lock
- **Kind:** INTERPRETIVE (structure and chart confirmation confidence penalty exists)
- **Judgment:** Explicit H4 long vs completed M15 distribution: no entry until they agree.

### P-199 — Lot growth from balance
- **Kind:** DETERMINISTIC overlap with position sizing
- **Judgment:** Size off closed balance, never off floating equity.

### P-200 — The market is right
- **Kind:** INTERPRETIVE
- **Judgment:** Charts are a probability map. Protect capital first; profit second.
