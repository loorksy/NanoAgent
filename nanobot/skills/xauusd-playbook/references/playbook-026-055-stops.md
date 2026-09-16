# Playbook P-026 … P-055 — Stop philosophy

Grep `P-0(2[6-9]|3[0-9]|4[0-9]|5[0-5])`.

### P-026 — The stop is not the support line
- **Kind:** INTERPRETIVE
- **Judgment:** A stop parked exactly under classic support is liquidity bait. Place invalidation beyond the hunt.

### P-027 — Stop-out wick as a new entry
- **Kind:** INTERPRETIVE
- **Judgment:** If the stop is tagged by a wick and price closes back in-range, that old stop is often the better fresh entry. New plan, new HITL — never a revenge add (P-184).

### P-028 — Mandatory buffer beyond the swing
- **Kind:** INTERPRETIVE (live buffers exist for overnight/post-news)
- **Judgment:** Always leave air under/over the swing so random gold noise does not kill a still-valid idea. Use structure plus ATR, not a memorized 30-point mantra.

### P-029 — ATR-based stop distance
- **Kind:** DETERMINISTIC multiplier available as `live().TRAIL_ATR_MULT` (also used as ATR-stop doctrine)
- **Judgment:** Measure stop air with ATR, not a fixed pip count. Structural invalidation still wins if it is farther.

### P-030 — Stop above the impulse bar (shorts)
- **Kind:** INTERPRETIVE
- **Judgment:** For sells, rest the stop above the breaking bar's wick, not above a distant historical high.

### P-031 — Structural stop, not a round pip count
- **Kind:** INTERPRETIVE
- **Judgment:** Kill the idea where the story dies. Ban "always 30 points."

### P-032 — Avoid round-number stops
- **Kind:** INTERPRETIVE
- **Judgment:** Makers hunt big figures. Park stops on ugly fractions.

### P-033 — Dynamic trendline as stop
- **Kind:** INTERPRETIVE
- **Judgment:** A close beyond the trendline can be the stop rule when that line is the idea.

### P-034 — Tighten after a confirmation bar
- **Kind:** INTERPRETIVE
- **Judgment:** Once an impulse bar prints in the trade's direction, pull the stop behind that bar's extreme.

### P-035 — Never widen a live stop
- **Kind:** INTERPRETIVE (hard discipline)
- **Judgment:** Forbidden to walk the stop farther to "give it room." Close or accept the planned loss.

### P-036 — Time stop
- **Kind:** DETERMINISTIC — `live().TIME_STOP_HOURS`
- **Judgment:** If gold chops in a dead box beyond the live time-stop, exit or tighten. Do not wait forever for the original target.

### P-037 — Behind equal lows / liquidity pools
- **Kind:** INTERPRETIVE
- **Judgment:** Rest stops beyond equal lows/highs with air. Those doubles are wick magnets.

### P-038 — Breakeven rule
- **Kind:** DETERMINISTIC reward-to-risk — `live().BREAKEVEN_RR`; timing is INTERPRETIVE
- **Judgment:** Move to entry only after price travels one times risk **and** a new M15 swing exists. Early BE is P-046.

### P-039 — Lock profits when most of the target is in
- **Kind:** DETERMINISTIC fractions — `PROFIT_LOCK_AT_TARGET_FRACTION` / `PROFIT_LOCK_KEEP_FRACTION`
- **Judgment:** When live fraction of the path is done, trail so a full give-back cannot turn green to red.

### P-040 — Order-block buffer
- **Kind:** INTERPRETIVE
- **Judgment:** Stop goes beyond the far side of the institutional block, not on its edge.

### P-041 — Shorts must include spread in the stop
- **Kind:** INTERPRETIVE (spread cap is spread guard)
- **Judgment:** For sells, add current spread into stop air so a wide ask does not fake-stop you.

### P-042 — Chandelier-style trail
- **Kind:** INTERPRETIVE using live ATR
- **Judgment:** Highest high of recent bars minus ATR multiple is a valid trailing rule.

### P-043 — Stop above the Asia sweep high (shorts)
- **Kind:** INTERPRETIVE
- **Judgment:** After a London sweep of Asia, stop sits beyond the sweep wick, not on the round Asia high.

### P-044 — Never stop inside an open FVG
- **Kind:** INTERPRETIVE
- **Judgment:** Price usually fills the gap. A stop in the middle of open imbalance is designed to be hit.

### P-045 — Momentum-break exit
- **Kind:** INTERPRETIVE
- **Judgment:** Two consecutive M5 closes against with rising momentum can justify leaving before the structural stop.

### P-046 — Do not BE too early
- **Kind:** INTERPRETIVE
- **Judgment:** BE before a minor high/low is taken often dies on a noise wick, then the real move starts.

### P-047 — Stop distance maps to portfolio percent via lot
- **Kind:** DETERMINISTIC — position sizing / `RISK_PCT_*`
- **Judgment:** Distance is structural; lot makes that distance equal live risk percent. Do not shrink the stop to "fit" a fantasy lot.

### P-048 — Close-based stop option
- **Kind:** INTERPRETIVE
- **Judgment:** Some ideas die only on an H1 close beyond the level, not on a wick. State that rule in the plan before entry.

### P-049 — Pre-news stop hygiene
- **Kind:** INTERPRETIVE (shield minutes are DETERMINISTIC news operational freeze)
- **Judgment:** Before red news, the stop should not sit in open gaps. Prefer flatten/BE per news shield rather than a heroic hold.

### P-050 — Split stops on split size
- **Kind:** INTERPRETIVE
- **Judgment:** Two tickets may use a tight stop and a structural stop. Combined risk still respects position sizing.

### P-051 — Channel median as early stop
- **Kind:** INTERPRETIVE
- **Judgment:** In a channel, losing the midline can be an early exit before the far rail.

### P-052 — Overnight extra air
- **Kind:** DETERMINISTIC — `live().OVERNIGHT_SL_BUFFER_POINTS`
- **Judgment:** Before rollover, add the live overnight buffer to absorb spread blowouts.

### P-053 — Shooting-star short stop
- **Kind:** INTERPRETIVE
- **Judgment:** Stop above the pin high with a small air gap, not on the round high.

### P-054 — Demand-zone full-wipe stop (longs)
- **Kind:** INTERPRETIVE
- **Judgment:** Long stop sits under the demand that ate the last sell wave, not under a random wick.

### P-055 — Manual kill on a clear opposite H1 pattern
- **Kind:** INTERPRETIVE
- **Judgment:** If a clean opposite head-and-shoulders completes on H1, propose exit. Do not wait for the original stop as a matter of pride.
