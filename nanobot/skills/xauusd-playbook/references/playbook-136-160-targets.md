# Playbook P-136 … P-160 — Targets and harvesting

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-136 … P-160 | `playbook-136-160-targets.md` | P-137 → `nanobot/trading/gates/trade_management.py::should_move_to_breakeven`<br>P-149 → `nanobot/trading/gates/pending_ttl.py::evaluate_pending_ttl`<br>P-153 → `nanobot/trading/gates/trade_management.py::partial_close_fraction` | P-136, P-138, P-139, P-140, P-141, P-142, P-143, P-144, P-145, P-146, P-147, P-148, P-150, P-151, P-152, P-154, P-155, P-156, P-157, P-158, P-159, P-160 |

## Contents

- [P-136 — Target is not always a flat S/R](#p-136-target-is-not-always-a-flat-sr)
- [P-137 — Forced partial at 1R](#p-137-forced-partial-at-1r)
- [P-138 — Open targets at ATH](#p-138-open-targets-at-ath)
- [P-139 — Exit before the round figure](#p-139-exit-before-the-round-figure)
- [P-140 — Time exit before NY close (scalps)](#p-140-time-exit-before-ny-close-scalps)
- [P-141 — Prior day high/low as the honest daily targets](#p-141-prior-day-highlow-as-the-honest-daily-targets)
- [P-142 — Do not flatten a marubozu at TP1](#p-142-do-not-flatten-a-marubozu-at-tp1)
- [P-143 — Extreme H1 RSI can be an exit](#p-143-extreme-h1-rsi-can-be-an-exit)
- [P-144 — Speed death](#p-144-speed-death)
- [P-145 — First opposing FVG is a target](#p-145-first-opposing-fvg-is-a-target)
- [P-146 — Leave the last stretch](#p-146-leave-the-last-stretch)
- [P-147 — After TP2, lock behind TP1](#p-147-after-tp2-lock-behind-tp1)
- [P-148 — Channel long targets the roof only](#p-148-channel-long-targets-the-roof-only)
- [P-149 — Collapse targets before red news](#p-149-collapse-targets-before-red-news)
- [P-150 — External liquidity as the real target](#p-150-external-liquidity-as-the-real-target)
- [P-151 — Add spread into long TP math](#p-151-add-spread-into-long-tp-math)
- [P-152 — Head-and-shoulders measured move](#p-152-head-and-shoulders-measured-move)
- [P-153 — Three-slice harvest](#p-153-three-slice-harvest)
- [P-154 — Lower-TF opposite pattern kills the higher-TF hold](#p-154-lower-tf-opposite-pattern-kills-the-higher-tf-hold)
- [P-155 — Promote a scalp to a swing only from a weekly-quality low](#p-155-promote-a-scalp-to-a-swing-only-from-a-weekly-quality-low)
- [P-156 — SMA50 as a correction target](#p-156-sma50-as-a-correction-target)
- [P-157 — Do not weekend-hold scalps](#p-157-do-not-weekend-hold-scalps)
- [P-158 — Liquidation-run target](#p-158-liquidation-run-target)
- [P-159 — Elliott third-wave minimum](#p-159-elliott-third-wave-minimum)
- [P-160 — Structure change beats leftover TP](#p-160-structure-change-beats-leftover-tp)


Grep `P-1(3[6-9]|4[0-9]|5[0-9]|60)`.

### P-136 — Target is not always a flat S/R
- **Kind:** INTERPRETIVE
- **Judgment:** TP1 may be a diagonal, a channel median, or an ATR multiple.

### P-137 — Forced partial at 1R
- **Kind:** DETERMINISTIC — `PARTIAL_TP1_FRACTION` + `BREAKEVEN_RR`
- **Judgment:** Bank the live TP1 fraction at 1R and move stop to entry per P-038.

### P-138 — Open targets at ATH
- **Kind:** INTERPRETIVE
- **Judgment:** No prior resistance: use 1.272 / 1.618 extensions, not a fantasy round number.

### P-139 — Exit before the round figure
- **Kind:** INTERPRETIVE
- **Judgment:** If the magnet is a big figure, take profit on the ugly print in front of it.

### P-140 — Time exit before NY close (scalps)
- **Kind:** INTERPRETIVE (daily-close lock is DETERMINISTIC P-195)
- **Judgment:** Flatten intraday scalps before NY close even if TP2 is untouched.

### P-141 — Prior day high/low as the honest daily targets
- **Kind:** INTERPRETIVE
- **Judgment:** PDH/PDL are the most reliable day targets on gold.

### P-142 — Do not flatten a marubozu at TP1
- **Kind:** INTERPRETIVE
- **Judgment:** If TP1 is hit by a full-body impulse, extend the runner. Momentum is not done.

### P-143 — Extreme H1 RSI can be an exit
- **Kind:** INTERPRETIVE
- **Judgment:** Manual exit if H1 RSI is violently stretched even if the mapped target is farther.

### P-144 — Speed death
- **Kind:** INTERPRETIVE
- **Judgment:** If a move that was one bar now takes ten bars, take the profit.

### P-145 — First opposing FVG is a target
- **Kind:** INTERPRETIVE
- **Judgment:** For longs, the first bearish FVG overhead is a primary scale-out.

### P-146 — Leave the last stretch
- **Kind:** INTERPRETIVE
- **Judgment:** Harvest most of the expected wave; the end is where gold reverses hardest.

### P-147 — After TP2, lock behind TP1
- **Kind:** INTERPRETIVE using live partial split
- **Judgment:** When TP2 hits, trail the runner so TP1 cannot be given back.

### P-148 — Channel long targets the roof only
- **Kind:** INTERPRETIVE
- **Judgment:** Buying the channel floor targets the roof, not a breakout fantasy.

### P-149 — Collapse targets before red news
- **Kind:** DETERMINISTIC overlap with news shield
- **Judgment:** If a winner is open inside the live shield window, close available profit. Do not "see what CPI does."

### P-150 — External liquidity as the real target
- **Kind:** INTERPRETIVE
- **Judgment:** A long from a low aims at the high that started the sell, not a random round number.

### P-151 — Add spread into long TP math
- **Kind:** INTERPRETIVE
- **Judgment:** Long TPs must still pay the spread on exit.

### P-152 — Head-and-shoulders measured move
- **Kind:** INTERPRETIVE
- **Judgment:** Project head-to-neckline from the break. That is the pattern target.

### P-153 — Three-slice harvest
- **Kind:** DETERMINISTIC — `live().PARTIAL_TP_SPLIT`
- **Judgment:** Obey the live 3-way split unless the operator's confirmed ticket says otherwise.

### P-154 — Lower-TF opposite pattern kills the higher-TF hold
- **Kind:** INTERPRETIVE
- **Judgment:** In an H1 long, a clean M5 double top is an exit, not a debate.

### P-155 — Promote a scalp to a swing only from a weekly-quality low
- **Kind:** INTERPRETIVE
- **Judgment:** Cancel the small day target only when the entry is a confirmed higher-TF low.

### P-156 — SMA50 as a correction target
- **Kind:** INTERPRETIVE
- **Judgment:** Corrective bounces often die at the 50-day average.

### P-157 — Do not weekend-hold scalps
- **Kind:** INTERPRETIVE (holiday/weekend locks may be session and calendar lock)
- **Judgment:** Avoid Saturday/Sunday gap risk. Flatten tactical books on Friday.

### P-158 — Liquidation-run target
- **Kind:** INTERPRETIVE
- **Judgment:** Aim through the cluster of resting stops, not just to the round number in front.

### P-159 — Elliott third-wave minimum
- **Kind:** INTERPRETIVE
- **Judgment:** If you are actually in a third wave, the minimum map is 1.618 of wave one. Do not force Elliott on a box.

### P-160 — Structure change beats leftover TP
- **Kind:** INTERPRETIVE
- **Judgment:** First broken M15 swing against you: bank whatever is left. Pride is not a target.
