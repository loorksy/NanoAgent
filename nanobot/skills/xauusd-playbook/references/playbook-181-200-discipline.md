# Playbook P-181 … P-200 — Execution discipline

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-181 … P-200 | `playbook-181-200-discipline.md` | P-183 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl`<br>P-184 → `nanobot/trading/gates/max_positions.py::evaluate_max_positions`<br>P-185 → `nanobot/trading/mt5_execution.py::mt5_propose_order`<br>P-186 → `nanobot/trading/intel/regex_emergency.py::scan_emergency`<br>P-187 → `nanobot/trading/gates/cooldown_lock.py::evaluate_cooldown_lock`<br>P-188 → `nanobot/trading/gates/position_sizing.py::evaluate_position_sizing`<br>P-189 → `nanobot/trading/gates/stale_quote.py::evaluate_stale_quote`<br>P-191 → `nanobot/trading/gates/drawdown_breaker.py::evaluate_drawdown_breaker`<br>P-193 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl`<br>P-195 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>P-196 → `nanobot/trading/gates/rr_filter.py::evaluate_rr_filter`<br>P-197 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>P-199 → `nanobot/trading/gates/position_sizing.py::evaluate_position_sizing` | P-181, P-190, P-192, P-194, P-198, P-200 |

## Contents

- [P-181 — Standing aside is a trade](#p-181-standing-aside-is-a-trade)
- [P-182 — Zero-hesitation auto-send — EXCLUDED](#p-182-zero-hesitation-auto-send--excluded)
- [P-183 — Pending TTL](#p-183-pending-ttl)
- [P-184 — No add to a same-side loser](#p-184-no-add-to-a-same-side-loser)
- [P-185 — Scalp vs swing isolation](#p-185-scalp-vs-swing-isolation)
- [P-186 — Unscheduled 1-minute explosion](#p-186-unscheduled-1-minute-explosion)
- [P-187 — Revenge freeze](#p-187-revenge-freeze)
- [P-188 — Dual lot check](#p-188-dual-lot-check)
- [P-189 — Fresh tick before send](#p-189-fresh-tick-before-send)
- [P-190 — Drop the bias when structure dies](#p-190-drop-the-bias-when-structure-dies)
- [P-191 — Daily max loss](#p-191-daily-max-loss)
- [P-192 — Marketable orders when the break is real](#p-192-marketable-orders-when-the-break-is-real)
- [P-193 — Half-distance pending cancel](#p-193-half-distance-pending-cancel)
- [P-194 — Comment the why on the ticket](#p-194-comment-the-why-on-the-ticket)
- [P-195 — No new risk into the daily close](#p-195-no-new-risk-into-the-daily-close)
- [P-196 — Live fill reward-to-risk](#p-196-live-fill-reward-to-risk)
- [P-197 — Official holidays off](#p-197-official-holidays-off)
- [P-198 — TF contradiction lock](#p-198-tf-contradiction-lock)
- [P-199 — Lot growth from balance](#p-199-lot-growth-from-balance)
- [P-200 — The market is right](#p-200-the-market-is-right)


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
- **Kind:** DETERMINISTIC — max positions losing-side check
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
