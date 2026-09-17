# Playbook P-106 … P-135 — Gold liquidity behaviour

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-106 … P-135 | `playbook-106-135-gold-liquidity.md` | P-118 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>P-127 → `nanobot/trading/gates/session_lock.py::evaluate_session_lock`<br>P-134 → `nanobot/trading/policy.py::GOLD_POINT` | P-106, P-107, P-108, P-109, P-110, P-111, P-112, P-113, P-114, P-115, P-116, P-117, P-119, P-120, P-121, P-122, P-123, P-124, P-125, P-126, P-128, P-129, P-130, P-131, P-132, P-133, P-135 |

## Contents

- [P-106 — Asia range sweep](#p-106-asia-range-sweep)
- [P-107 — Gold does not forgive a late stop](#p-107-gold-does-not-forgive-a-late-stop)
- [P-108 — Big-figure traps](#p-108-big-figure-traps)
- [P-109 — New York open candle](#p-109-new-york-open-candle)
- [P-110 — Fear rally overrides charts](#p-110-fear-rally-overrides-charts)
- [P-111 — Temporary DXY decoupling](#p-111-temporary-dxy-decoupling)
- [P-112 — Normal gold day range](#p-112-normal-gold-day-range)
- [P-113 — First news wick is a trap](#p-113-first-news-wick-is-a-trap)
- [P-114 — Equal highs and lows will be taken](#p-114-equal-highs-and-lows-will-be-taken)
- [P-115 — Liquidity voids fill later](#p-115-liquidity-voids-fill-later)
- [P-116 — Gold loves deep 0.786](#p-116-gold-loves-deep-0786)
- [P-117 — London PM fixing window](#p-117-london-pm-fixing-window)
- [P-118 — Midnight spread trap](#p-118-midnight-spread-trap)
- [P-119 — True support break becomes a vertical dump](#p-119-true-support-break-becomes-a-vertical-dump)
- [P-120 — Do not chase a vertical green](#p-120-do-not-chase-a-vertical-green)
- [P-121 — Real yields cap gold on higher TFs](#p-121-real-yields-cap-gold-on-higher-tfs)
- [P-122 — Friday flattening](#p-122-friday-flattening)
- [P-123 — Monday first hour](#p-123-monday-first-hour)
- [P-124 — Oscillators die in a tight box](#p-124-oscillators-die-in-a-tight-box)
- [P-125 — Safe-haven dip buy](#p-125-safe-haven-dip-buy)
- [P-126 — Silver leads](#p-126-silver-leads)
- [P-127 — US bank holidays are dead](#p-127-us-bank-holidays-are-dead)
- [P-128 — Late New York fade](#p-128-late-new-york-fade)
- [P-129 — Prior day close is a magnet](#p-129-prior-day-close-is-a-magnet)
- [P-130 — H4 200 EMA regime](#p-130-h4-200-ema-regime)
- [P-131 — NFP eve stagnation](#p-131-nfp-eve-stagnation)
- [P-132 — Miners as a lead](#p-132-miners-as-a-lead)
- [P-133 — Bollinger walk then snap](#p-133-bollinger-walk-then-snap)
- [P-134 — Point math](#p-134-point-math)
- [P-135 — Slow grind up, violent down](#p-135-slow-grind-up-violent-down)


Grep `P-1(0[6-9]|1[0-9]|2[0-9]|3[0-5])`.

### P-106 — Asia range sweep
- **Kind:** INTERPRETIVE
- **Judgment:** Most London opens take Asia high or low, then reverse. Do not treat the first London break of Asia as the day's trend until it holds.

### P-107 — Gold does not forgive a late stop
- **Kind:** INTERPRETIVE
- **Judgment:** Once the reverse starts, a small planned loss beats hoping. Gold can run hundreds of points without a pause.

### P-108 — Big-figure traps
- **Kind:** INTERPRETIVE
- **Judgment:** Around major figures gold often fake-breaks by a wide band to dump retail before the real move.

### P-109 — New York open candle
- **Kind:** INTERPRETIVE
- **Judgment:** The New York open bar can erase London in minutes. Scalps should already be flat or fully protected.

### P-110 — Fear rally overrides charts
- **Kind:** INTERPRETIVE
- **Judgment:** On sudden military headlines, technicals yield. Gold is bought as a fact. Still HITL for orders.

### P-111 — Temporary DXY decoupling
- **Kind:** INTERPRETIVE
- **Judgment:** Gold can rise with the dollar in banking panic. Inverse-dollar is not a holy rule.

### P-112 — Normal gold day range
- **Kind:** INTERPRETIVE context (ADR chase cap is DETERMINISTIC)
- **Judgment:** Quiet sub-normal days often have not started. Do not force a trend from a dead box. Exact ADR numbers are live/tool output, not memorized.

### P-113 — First news wick is a trap
- **Kind:** INTERPRETIVE (void seconds DETERMINISTIC N-035)
- **Judgment:** The first seconds after CPI/FOMC are usually a contrary sweep, then the real path.

### P-114 — Equal highs and lows will be taken
- **Kind:** INTERPRETIVE
- **Judgment:** Gold rarely leaves equal highs/lows unstolen, even days later. Plan for the hunt.

### P-115 — Liquidity voids fill later
- **Kind:** INTERPRETIVE
- **Judgment:** News marubozu gaps usually attract at least a partial fill later. Do not park stops inside them.

### P-116 — Gold loves deep 0.786
- **Kind:** INTERPRETIVE
- **Judgment:** Unlike many FX pairs that bounce 50–61.8, gold often drags to 0.786 to take more stops.

### P-117 — London PM fixing window
- **Kind:** INTERPRETIVE
- **Judgment:** Around the London PM gold fix, expect sudden inventory flattening. Not a session and calendar lock lock unless it overlaps live session rules.

### P-118 — Midnight spread trap
- **Kind:** DETERMINISTIC — session and calendar lock / `MIDNIGHT_SPREAD_*`
- **Judgment:** Rollover minutes: no new risk, no tight stops. Obey the live clock.

### P-119 — True support break becomes a vertical dump
- **Kind:** INTERPRETIVE
- **Judgment:** If gold loses real support and two H1 bodies hold below, it often does not "correct" — it seeks the next historical shelf.

### P-120 — Do not chase a vertical green
- **Kind:** INTERPRETIVE
- **Judgment:** Buying after a huge five-minute spike is late. Buy the coil before the explosion, or skip.

### P-121 — Real yields cap gold on higher TFs
- **Kind:** INTERPRETIVE
- **Judgment:** Rising TIPS/real yields are a persistent lid on D1 gold. Use as macro weight, not a scalp trigger.

### P-122 — Friday flattening
- **Kind:** INTERPRETIVE
- **Judgment:** Friday closes often see fund de-risk. Late-week fades against the weekly trend are common. Weekend gap risk is P-157.

### P-123 — Monday first hour
- **Kind:** INTERPRETIVE
- **Judgment:** Week-open noise often fills weekend gaps. Do not treat it as Monday's trend until it holds.

### P-124 — Oscillators die in a tight box
- **Kind:** INTERPRETIVE
- **Judgment:** RSI/stoch in a ~ATR-small range spam false signals. Ban oscillator entries there.

### P-125 — Safe-haven dip buy
- **Kind:** INTERPRETIVE
- **Judgment:** On geopolitical panic days, every small dip is a long until de-escalation (N-093).

### P-126 — Silver leads
- **Kind:** INTERPRETIVE
- **Judgment:** If silver breaks its high and gold lags, gold usually catches up fast.

### P-127 — US bank holidays are dead
- **Kind:** DETERMINISTIC overlap with session and calendar lock holidays
- **Judgment:** US holiday sessions are spread-burn. Prefer the holiday lock over "just a scalp."

### P-128 — Late New York fade
- **Kind:** INTERPRETIVE
- **Judgment:** Late NY often mean-reverts the day's path. Scalps should already be done.

### P-129 — Prior day close is a magnet
- **Kind:** INTERPRETIVE
- **Judgment:** Previous-day close acts as invisible S/R on gold. Map it.

### P-130 — H4 200 EMA regime
- **Kind:** INTERPRETIVE
- **Judgment:** Above H4 200 EMA prefer longs; below prefer shorts. Exceptions need macro panic or a CHoCH plus reclaim.

### P-131 — NFP eve stagnation
- **Kind:** INTERPRETIVE (freeze is DETERMINISTIC)
- **Judgment:** The day before NFP is a tight box. Trading inside it is death by spread.

### P-132 — Miners as a lead
- **Kind:** INTERPRETIVE
- **Judgment:** GDX/miners can lead spot by hours. Use as a tell, not an executable gold lot.

### P-133 — Bollinger walk then snap
- **Kind:** INTERPRETIVE
- **Judgment:** A full H1 body outside the outer band warns of a snap to the midline. Do not add in the direction of the stretch.

### P-134 — Point math
- **Kind:** DETERMINISTIC — `GOLD_POINT` ($1 = 100 points)
- **Judgment:** Risk math uses this scale. Never mix "pips" from FX into gold lots.

### P-135 — Slow grind up, violent down
- **Kind:** INTERPRETIVE
- **Judgment:** Gold often climbs for days and dumps in hours. Trail longs; do not assume a dump will be polite.
