# Spec coverage — P-001…P-200 / N-001…N-100 / C-001…C-100

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-001 … P-200 / N-001 … N-100 / C-001 … C-100 | `spec-coverage.md` | Python file + function + test in each DETERMINISTIC row | reference file + heading in each INTERPRETIVE row |

Grep a rule id. DETERMINISTIC rows name the Python function and the test that
proves a veto/modify/block. INTERPRETIVE rows name the reference heading.
EXCLUDED is allowed only for backtest, unpaid-service gaps, or P-182 HITL conflict.

| Id | Class | Why | Destination | Invocation |
| --- | --- | --- | --- | --- |
| P-001 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-001 — Beyond classic support and resistance` | documentation-only interpretive |
| P-002 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-002 — Immediate entry when the story is complete` | documentation-only interpretive |
| P-003 | INTERPRETIVE | INTERPRETIVE (reward-to-risk floor is DETERMINISTIC) | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-003 — Distance vs target paradox` | documentation-only interpretive |
| P-004 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-004 — Front-run explosive closes` | documentation-only interpretive |
| P-005 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-005 — Incomplete bounce (front-running the level)` | documentation-only interpretive |
| P-006 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-006 — Enter from FVG, not the broken high` | documentation-only interpretive |
| P-007 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-007 — Counter engulfing as enough` | documentation-only interpretive |
| P-008 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-008 — Session-open range break` | documentation-only interpretive |
| P-009 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-009 — Equilibrium entries` | documentation-only interpretive |
| P-010 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-010 — Two-timeframe timing` | documentation-only interpretive |
| P-011 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-011 — Trendline fan, steepest first` | documentation-only interpretive |
| P-012 | DETERMINISTIC | DETERMINISTIC — `live().IDEA_STALE_HOURS` / pending TTL (pending-order validity uses the stricter pending TTL) | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_ttl_and_half_distance` | invoked from recommendation path; invoked from MT5 execution path |
| P-013 | INTERPRETIVE | INTERPRETIVE (news freeze is DETERMINISTIC) | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-013 — News-candle tail as support` | documentation-only interpretive |
| P-014 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-014 — Absorption as entry` | documentation-only interpretive |
| P-015 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-015 — Break of the small counter-trendline` | documentation-only interpretive |
| P-016 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-016 — Do not wait for a deep pullback in a steep trend` | documentation-only interpretive |
| P-017 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-017 — Round-number reactions` | documentation-only interpretive |
| P-018 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-018 — Failed bear pattern becomes a long` | documentation-only interpretive |
| P-019 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-019 — Three white soldiers after a box` | documentation-only interpretive |
| P-020 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-020 — Range reclaim` | documentation-only interpretive |
| P-021 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-021 — Hourly close timing` | documentation-only interpretive |
| P-022 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-022 — Fast EMA as dynamic entry in trends` | documentation-only interpretive |
| P-023 | INTERPRETIVE | INTERPRETIVE (200% ADR chase ban is DETERMINISTIC news 82) | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-023 — Fade an exhausted ADR day` | documentation-only interpretive |
| P-024 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-024 — Split entries` | documentation-only interpretive |
| P-025 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-001-025-entry.md` / `P-025 — Broken high that flips to support` | documentation-only interpretive |
| P-026 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-026 — The stop is not the support line` | documentation-only interpretive |
| P-027 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-027 — Stop-out wick as a new entry` | documentation-only interpretive |
| P-028 | INTERPRETIVE | INTERPRETIVE (live buffers exist for overnight/post-news) | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-028 — Mandatory buffer beyond the swing` | documentation-only interpretive |
| P-029 | DETERMINISTIC | DETERMINISTIC multiplier available as `live().TRAIL_ATR_MULT` (also used as ATR-stop doctrine) | `nanobot/trading/gates/trade_management.py` `trailing_stop` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| P-030 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-030 — Stop above the impulse bar (shorts)` | documentation-only interpretive |
| P-031 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-031 — Structural stop, not a round pip count` | documentation-only interpretive |
| P-032 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-032 — Avoid round-number stops` | documentation-only interpretive |
| P-033 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-033 — Dynamic trendline as stop` | documentation-only interpretive |
| P-034 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-034 — Tighten after a confirmation bar` | documentation-only interpretive |
| P-035 | INTERPRETIVE | INTERPRETIVE (hard discipline) | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-035 — Never widen a live stop` | documentation-only interpretive |
| P-036 | DETERMINISTIC | DETERMINISTIC — `live().TIME_STOP_HOURS` | `nanobot/trading/gates/time_stop.py` `evaluate_time_stop` `tests/trading/test_risk_gates.py::test_time_stop_and_overnight_buffer` | invoked from MT5 execution path |
| P-037 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-037 — Behind equal lows / liquidity pools` | documentation-only interpretive |
| P-038 | DETERMINISTIC | DETERMINISTIC reward-to-risk — `live().BREAKEVEN_RR`; timing is INTERPRETIVE | `nanobot/trading/gates/trade_management.py` `should_move_to_breakeven` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| P-039 | DETERMINISTIC | DETERMINISTIC fractions — `PROFIT_LOCK_AT_TARGET_FRACTION` / `PROFIT_LOCK_KEEP_FRACTION` | `nanobot/trading/gates/trade_management.py` `management_snapshot` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| P-040 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-040 — Order-block buffer` | documentation-only interpretive |
| P-041 | INTERPRETIVE | INTERPRETIVE (spread cap is spread guard) | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-041 — Shorts must include spread in the stop` | documentation-only interpretive |
| P-042 | INTERPRETIVE | INTERPRETIVE using live ATR | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-042 — Chandelier-style trail` | documentation-only interpretive |
| P-043 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-043 — Stop above the Asia sweep high (shorts)` | documentation-only interpretive |
| P-044 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-044 — Never stop inside an open FVG` | documentation-only interpretive |
| P-045 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-045 — Momentum-break exit` | documentation-only interpretive |
| P-046 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-046 — Do not BE too early` | documentation-only interpretive |
| P-047 | DETERMINISTIC | DETERMINISTIC — position sizing / `RISK_PCT_*` | `nanobot/trading/gates/position_sizing.py` `evaluate_position_sizing` `tests/trading/test_risk_gates.py::test_position_sizing_dual_check` | invoked from recommendation path; invoked from MT5 execution path |
| P-048 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-048 — Close-based stop option` | documentation-only interpretive |
| P-049 | INTERPRETIVE | INTERPRETIVE (shield minutes are DETERMINISTIC news operational freeze) | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-049 — Pre-news stop hygiene` | documentation-only interpretive |
| P-050 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-050 — Split stops on split size` | documentation-only interpretive |
| P-051 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-051 — Channel median as early stop` | documentation-only interpretive |
| P-052 | DETERMINISTIC | DETERMINISTIC — `live().OVERNIGHT_SL_BUFFER_POINTS` | `nanobot/trading/gates/trade_management.py` `overnight_stop` `tests/trading/test_risk_gates.py::test_time_stop_and_overnight_buffer` | invoked from MT5 execution path |
| P-053 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-053 — Shooting-star short stop` | documentation-only interpretive |
| P-054 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-054 — Demand-zone full-wipe stop (longs)` | documentation-only interpretive |
| P-055 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-026-055-stops.md` / `P-055 — Manual kill on a clear opposite H1 pattern` | documentation-only interpretive |
| P-056 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-056 — A retest is not mandatory` | documentation-only interpretive |
| P-057 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-057 — Slow retest can be a failed break` | documentation-only interpretive |
| P-058 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-058 — Deep retest` | documentation-only interpretive |
| P-059 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-059 — Retest bar quality` | documentation-only interpretive |
| P-060 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-060 — Retest the trendline, not the horizontal` | documentation-only interpretive |
| P-061 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-061 — Fake retest to fill resting orders` | documentation-only interpretive |
| P-062 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-062 — Failed retest becomes the opposite trade` | documentation-only interpretive |
| P-063 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-063 — Lower-timeframe retest inside an H1 "straight" break` | documentation-only interpretive |
| P-064 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-064 — Low-volume retests are safer` | documentation-only interpretive |
| P-065 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-065 — Fibonacci retest vs the break price` | documentation-only interpretive |
| P-066 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-066 — Head-and-shoulders right shoulder` | documentation-only interpretive |
| P-067 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-067 — Many retests weaken the level` | documentation-only interpretive |
| P-068 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-068 — Time contrast` | documentation-only interpretive |
| P-069 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-069 — Zones, not lines` | documentation-only interpretive |
| P-070 | INTERPRETIVE | INTERPRETIVE (gap no-chase on open is DETERMINISTIC news 90) | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-070 — Weekly opening gap as a later magnet` | documentation-only interpretive |
| P-071 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-071 — Runaway break when DXY confirms` | documentation-only interpretive |
| P-072 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-072 — Confirm a retest with a rejection bar` | documentation-only interpretive |
| P-073 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-073 — Broken Asia low, bounce-to-fail` | documentation-only interpretive |
| P-074 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-074 — Mid-air retest` | documentation-only interpretive |
| P-075 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-075 — Parallel channel outside` | documentation-only interpretive |
| P-076 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-076 — Psychological figures as retests` | documentation-only interpretive |
| P-077 | INTERPRETIVE | INTERPRETIVE (entry wait is DETERMINISTIC) | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-077 — Post-news quiet retest` | documentation-only interpretive |
| P-078 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-078 — All-time-high retest is often a sideways box` | documentation-only interpretive |
| P-079 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-079 — Oversold H4 + broken resistance` | documentation-only interpretive |
| P-080 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-056-080-retest.md` / `P-080 — Cancel the retest if the pullback is too deep` | documentation-only interpretive |
| P-081 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-081 — Inner and outer lines together` | documentation-only interpretive |
| P-082 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-082 — A line is a band` | documentation-only interpretive |
| P-083 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-083 — Bounce from the diagonal, ignore the horizontal` | documentation-only interpretive |
| P-084 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-084 — Third touch vs fourth` | documentation-only interpretive |
| P-085 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-085 — Breaking the line is not automatically a reversal` | documentation-only interpretive |
| P-086 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-086 — Adjust after a wick-and-reclaim` | documentation-only interpretive |
| P-087 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-087 — Parallel channel roof as a must-take target` | documentation-only interpretive |
| P-088 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-088 — Right-angle separation` | documentation-only interpretive |
| P-089 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-089 — Confirm a horizontal bounce with a small trendline break` | documentation-only interpretive |
| P-090 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-090 — Obvious lines are liquidity` | documentation-only interpretive |
| P-091 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-091 — Counter-trendlines for scalps` | documentation-only interpretive |
| P-092 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-092 — Channel median magnet` | documentation-only interpretive |
| P-093 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-093 — Diagonal plus horizontal confluence` | documentation-only interpretive |
| P-094 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-094 — Break then retest of a trendline` | documentation-only interpretive |
| P-095 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-095 — Body-based lines beat wick-based lines` | documentation-only interpretive |
| P-096 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-096 — Speed fans` | documentation-only interpretive |
| P-097 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-097 — RSI trendline leads price` | documentation-only interpretive |
| P-098 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-098 — Daily lines need macro force to die` | documentation-only interpretive |
| P-099 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-099 — Too far from the rising line — no fresh longs` | documentation-only interpretive |
| P-100 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-100 — Double-top trendline vs neckline` | documentation-only interpretive |
| P-101 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-101 — Broken rising line becomes a roof` | documentation-only interpretive |
| P-102 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-102 — Symmetrical triangle` | documentation-only interpretive |
| P-103 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-103 — Opposite falling line as a moving target` | documentation-only interpretive |
| P-104 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-104 — Doji "breaks" are false` | documentation-only interpretive |
| P-105 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-081-105-trendlines.md` / `P-105 — London open plus rising-line tag` | documentation-only interpretive |
| P-106 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-106 — Asia range sweep` | documentation-only interpretive |
| P-107 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-107 — Gold does not forgive a late stop` | documentation-only interpretive |
| P-108 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-108 — Big-figure traps` | documentation-only interpretive |
| P-109 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-109 — New York open candle` | documentation-only interpretive |
| P-110 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-110 — Fear rally overrides charts` | documentation-only interpretive |
| P-111 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-111 — Temporary DXY decoupling` | documentation-only interpretive |
| P-112 | INTERPRETIVE | INTERPRETIVE context (ADR chase cap is DETERMINISTIC) | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-112 — Normal gold day range` | documentation-only interpretive |
| P-113 | INTERPRETIVE | INTERPRETIVE (void seconds DETERMINISTIC N-035) | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-113 — First news wick is a trap` | documentation-only interpretive |
| P-114 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-114 — Equal highs and lows will be taken` | documentation-only interpretive |
| P-115 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-115 — Liquidity voids fill later` | documentation-only interpretive |
| P-116 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-116 — Gold loves deep 0.786` | documentation-only interpretive |
| P-117 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-117 — London PM fixing window` | documentation-only interpretive |
| P-118 | DETERMINISTIC | DETERMINISTIC — session and calendar lock / `MIDNIGHT_SPREAD_*` | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_midnight_and_holiday` | invoked from recommendation path; invoked from MT5 execution path |
| P-119 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-119 — True support break becomes a vertical dump` | documentation-only interpretive |
| P-120 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-120 — Do not chase a vertical green` | documentation-only interpretive |
| P-121 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-121 — Real yields cap gold on higher TFs` | documentation-only interpretive |
| P-122 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-122 — Friday flattening` | documentation-only interpretive |
| P-123 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-123 — Monday first hour` | documentation-only interpretive |
| P-124 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-124 — Oscillators die in a tight box` | documentation-only interpretive |
| P-125 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-125 — Safe-haven dip buy` | documentation-only interpretive |
| P-126 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-126 — Silver leads` | documentation-only interpretive |
| P-127 | DETERMINISTIC | DETERMINISTIC overlap with session and calendar lock holidays | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_midnight_and_holiday` | invoked from recommendation path; invoked from MT5 execution path |
| P-128 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-128 — Late New York fade` | documentation-only interpretive |
| P-129 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-129 — Prior day close is a magnet` | documentation-only interpretive |
| P-130 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-130 — H4 200 EMA regime` | documentation-only interpretive |
| P-131 | INTERPRETIVE | INTERPRETIVE (freeze is DETERMINISTIC) | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-131 — NFP eve stagnation` | documentation-only interpretive |
| P-132 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-132 — Miners as a lead` | documentation-only interpretive |
| P-133 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-133 — Bollinger walk then snap` | documentation-only interpretive |
| P-134 | DETERMINISTIC | DETERMINISTIC — `GOLD_POINT` ($1 = 100 points) | `nanobot/trading/policy.py` `GOLD_POINT` `tests/trading/test_risk_gates.py::test_bad_tick` | invoked from recommendation path; invoked from MT5 execution path |
| P-135 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-106-135-gold-liquidity.md` / `P-135 — Slow grind up, violent down` | documentation-only interpretive |
| P-136 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-136 — Target is not always a flat S/R` | documentation-only interpretive |
| P-137 | DETERMINISTIC | DETERMINISTIC — `PARTIAL_TP1_FRACTION` + `BREAKEVEN_RR` | `nanobot/trading/gates/trade_management.py` `should_move_to_breakeven` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| P-138 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-138 — Open targets at ATH` | documentation-only interpretive |
| P-139 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-139 — Exit before the round figure` | documentation-only interpretive |
| P-140 | INTERPRETIVE | INTERPRETIVE (daily-close lock is DETERMINISTIC P-195) | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-140 — Time exit before NY close (scalps)` | documentation-only interpretive |
| P-141 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-141 — Prior day high/low as the honest daily targets` | documentation-only interpretive |
| P-142 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-142 — Do not flatten a marubozu at TP1` | documentation-only interpretive |
| P-143 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-143 — Extreme H1 RSI can be an exit` | documentation-only interpretive |
| P-144 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-144 — Speed death` | documentation-only interpretive |
| P-145 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-145 — First opposing FVG is a target` | documentation-only interpretive |
| P-146 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-146 — Leave the last stretch` | documentation-only interpretive |
| P-147 | INTERPRETIVE | INTERPRETIVE using live partial split | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-147 — After TP2, lock behind TP1` | documentation-only interpretive |
| P-148 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-148 — Channel long targets the roof only` | documentation-only interpretive |
| P-149 | DETERMINISTIC | DETERMINISTIC overlap with news shield | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_cancel_before_news` | invoked from recommendation path; invoked from MT5 execution path |
| P-150 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-150 — External liquidity as the real target` | documentation-only interpretive |
| P-151 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-151 — Add spread into long TP math` | documentation-only interpretive |
| P-152 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-152 — Head-and-shoulders measured move` | documentation-only interpretive |
| P-153 | DETERMINISTIC | DETERMINISTIC — `live().PARTIAL_TP_SPLIT` | `nanobot/trading/gates/trade_management.py` `partial_close_fraction` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| P-154 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-154 — Lower-TF opposite pattern kills the higher-TF hold` | documentation-only interpretive |
| P-155 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-155 — Promote a scalp to a swing only from a weekly-quality low` | documentation-only interpretive |
| P-156 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-156 — SMA50 as a correction target` | documentation-only interpretive |
| P-157 | INTERPRETIVE | INTERPRETIVE (holiday/weekend locks may be session and calendar lock) | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-157 — Do not weekend-hold scalps` | documentation-only interpretive |
| P-158 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-158 — Liquidation-run target` | documentation-only interpretive |
| P-159 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-159 — Elliott third-wave minimum` | documentation-only interpretive |
| P-160 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-136-160-targets.md` / `P-160 — Structure change beats leftover TP` | documentation-only interpretive |
| P-161 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-161 — Hammer in the middle of nowhere` | documentation-only interpretive |
| P-162 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-162 — Quiet break is not a break` | documentation-only interpretive |
| P-163 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-163 — Doji is pause, not reversal` | documentation-only interpretive |
| P-164 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-164 — Failed engulfing` | documentation-only interpretive |
| P-165 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-165 — Shooting star at ATH` | documentation-only interpretive |
| P-166 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-166 — Shrinking bodies = seller exhaustion` | documentation-only interpretive |
| P-167 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-167 — Micro new highs with long wicks` | documentation-only interpretive |
| P-168 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-168 — Inside-bar coil` | documentation-only interpretive |
| P-169 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-169 — First London M15 trap` | documentation-only interpretive |
| P-170 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-170 — Close in the top quarter` | documentation-only interpretive |
| P-171 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-171 — Five greens in a row on M15` | documentation-only interpretive |
| P-172 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-172 — Double rejection wicks` | documentation-only interpretive |
| P-173 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-173 — Absorption bar` | documentation-only interpretive |
| P-174 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-174 — Prior-day low wick reclaim` | documentation-only interpretive |
| P-175 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-175 — Strong trends lack noisy wicks` | documentation-only interpretive |
| P-176 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-176 — Range-box fake-then-opposite` | documentation-only interpretive |
| P-177 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-177 — Selling climax` | documentation-only interpretive |
| P-178 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-178 — Bodies tell the truth, wicks hunt` | documentation-only interpretive |
| P-179 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-179 — Not every gap must fill now` | documentation-only interpretive |
| P-180 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-161-180-candle-traps.md` / `P-180 — Spinning tops on support` | documentation-only interpretive |
| P-181 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-181 — Standing aside is a trade` | documentation-only interpretive |
| P-182 | EXCLUDED | EXCLUDED | not implemented — HITL propose/confirm is mandatory | excluded |
| P-183 | DETERMINISTIC | DETERMINISTIC — `live().PENDING_TTL_HOURS` / pending-order validity | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_ttl_and_half_distance` | invoked from recommendation path; invoked from MT5 execution path |
| P-184 | DETERMINISTIC | DETERMINISTIC — max positions losing-side check | `nanobot/trading/gates/max_positions.py` `evaluate_max_positions` `tests/trading/test_risk_gates.py::test_no_double_losing_side` | invoked from recommendation path; invoked from MT5 execution path |
| P-185 | DETERMINISTIC | DETERMINISTIC identifiers — `MAGIC_SCALP` / `MAGIC_SWING` | `nanobot/trading/mt5_execution.py` `mt5_propose_order` `tests/trading/test_mt5_hitl.py::test_propose_does_not_send` | invoked from MT5 execution path |
| P-186 | DETERMINISTIC | DETERMINISTIC — `EMERGENCY_MOVE_POINTS_PER_MINUTE` plus FEATURE-05 | `nanobot/trading/intel/regex_emergency.py` `scan_emergency` `tests/trading/test_intel_engines.py::test_regex_emergency_war_and_lock` | invoked from recommendation path |
| P-187 | DETERMINISTIC | DETERMINISTIC — cooldown lock / consecutive-loss minutes (session cooldown vs consecutive-loss cooldown: code uses the stricter policy) | `nanobot/trading/gates/cooldown_lock.py` `evaluate_cooldown_lock` `tests/trading/test_risk_gates.py::test_cooldown_lock_blocks_while_active` | invoked from recommendation path; invoked from MT5 execution path |
| P-188 | DETERMINISTIC | DETERMINISTIC — position sizing / `LOT_DUAL_CHECK_*` | `nanobot/trading/gates/position_sizing.py` `evaluate_position_sizing` `tests/trading/test_risk_gates.py::test_position_sizing_dual_check` | invoked from recommendation path; invoked from MT5 execution path |
| P-189 | DETERMINISTIC | DETERMINISTIC — live quote freshness / `STALE_QUOTE_SECONDS` | `nanobot/trading/gates/stale_quote.py` `evaluate_stale_quote` `tests/trading/test_risk_gates.py::test_stale_quote` | invoked from recommendation path; invoked from MT5 execution path |
| P-190 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-190 — Drop the bias when structure dies` | documentation-only interpretive |
| P-191 | DETERMINISTIC | DETERMINISTIC — drawdown and kill switch / `DAILY_DRAWDOWN_PCT` | `nanobot/trading/gates/drawdown_breaker.py` `evaluate_drawdown_breaker` `tests/trading/test_risk_gates.py::test_drawdown_breaker_and_kill_switch` | invoked from recommendation path; invoked from MT5 execution path |
| P-192 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-192 — Marketable orders when the break is real` | documentation-only interpretive |
| P-193 | DETERMINISTIC | DETERMINISTIC — pending-order validity / `HALF_DISTANCE_FRACTION` | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_ttl_and_half_distance` | invoked from recommendation path; invoked from MT5 execution path |
| P-194 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-194 — Comment the why on the ticket` | documentation-only interpretive |
| P-195 | DETERMINISTIC | DETERMINISTIC — session and calendar lock / `DAILY_CLOSE_LOCK_MINUTES` | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_midnight_and_holiday` | invoked from recommendation path; invoked from MT5 execution path |
| P-196 | DETERMINISTIC | DETERMINISTIC — confirm path / `MIN_RR_LIVE_FILL` | `nanobot/trading/gates/rr_filter.py` `evaluate_rr_filter` `tests/trading/test_risk_gates.py::test_rr_live_fill_blocks_when_degraded` | invoked from recommendation path; invoked from MT5 execution path |
| P-197 | DETERMINISTIC | DETERMINISTIC — session and calendar lock holiday calendar | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_midnight_and_holiday` | invoked from recommendation path; invoked from MT5 execution path |
| P-198 | INTERPRETIVE | INTERPRETIVE (structure and chart confirmation confidence penalty exists) | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-198 — TF contradiction lock` | documentation-only interpretive |
| P-199 | DETERMINISTIC | DETERMINISTIC overlap with position sizing | `nanobot/trading/gates/position_sizing.py` `evaluate_position_sizing` `tests/trading/test_risk_gates.py::test_position_sizing_dual_check` | invoked from recommendation path; invoked from MT5 execution path |
| P-200 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/xauusd-playbook/references/playbook-181-200-discipline.md` / `P-200 — The market is right` | documentation-only interpretive |
| N-001 | DETERMINISTIC | DETERMINISTIC — news and event shield blackout is stricter than this 15-minute rule (`NEWS_BLACKOUT_BEFORE_MINUTES`) | `nanobot/trading/gates/news_window.py` `evaluate_news_window` `tests/trading/test_risk_gates.py::test_news_window_still_blocks_thirty_minutes_before` | invoked from recommendation path |
| N-002 | DETERMINISTIC | DETERMINISTIC — news operational freeze / `NEWS_SHIELD_MINUTES` | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_cancel_before_news` | invoked from recommendation path; invoked from MT5 execution path |
| N-003 | DETERMINISTIC | DETERMINISTIC overlap with news operational freeze | `nanobot/trading/gates/news_operational.py` `evaluate_news_operational` `tests/trading/test_risk_gates.py::test_news_operational_freeze_and_void` | invoked from recommendation path; invoked from MT5 execution path |
| N-004 | DETERMINISTIC | DETERMINISTIC — `FLAT_NEAR_ENTRY_POINTS` | `nanobot/trading/gates/news_operational.py` `evaluate_news_operational` `tests/trading/test_risk_gates.py::test_news_operational_freeze_and_void` | invoked from recommendation path; invoked from MT5 execution path |
| N-005 | DETERMINISTIC | DETERMINISTIC — `SPREAD_MULTIPLIER_PRE_NEWS` / `SPREAD_PRE_NEWS_MINUTES` | `nanobot/trading/gates/spread_guard.py` `evaluate_spread_guard` `tests/trading/test_risk_gates.py::test_spread_guard_pre_news_multiplier` | invoked from recommendation path; invoked from MT5 execution path |
| N-006 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-006 — Priced-in tape` | documentation-only interpretive |
| N-007 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-007 — Map the pre-news box` | documentation-only interpretive |
| N-008 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-008 — Disable tight trails into the print` | documentation-only interpretive |
| N-009 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-009 — Stacked releases` | documentation-only interpretive |
| N-010 | DETERMINISTIC | DETERMINISTIC — `PING_MAX_MS` | `nanobot/trading/gates/stale_quote.py` `evaluate_stale_quote` `tests/trading/test_risk_gates.py::test_stale_quote` | invoked from recommendation path; invoked from MT5 execution path |
| N-011 | DETERMINISTIC | DETERMINISTIC — session and calendar lock rollover + news | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_rollover_only_near_news` | invoked from recommendation path; invoked from MT5 execution path |
| N-012 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-012 — Surprise threshold` | documentation-only interpretive |
| N-013 | INTERPRETIVE | INTERPRETIVE (calendar still drives news and event shield) | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-013 — Chair testimony day` | documentation-only interpretive |
| N-014 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-014 — DXY leak before the print` | documentation-only interpretive |
| N-015 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-015 — Map 150–300-point shelves` | documentation-only interpretive |
| N-016 | DETERMINISTIC | DETERMINISTIC — `RISK_PCT_NEWS_DAY` / position sizing | `nanobot/trading/gates/position_sizing.py` `evaluate_position_sizing` `tests/trading/test_risk_gates.py::test_position_sizing_dual_check` | invoked from recommendation path; invoked from MT5 execution path |
| N-017 | INTERPRETIVE | INTERPRETIVE (slippage slippage and latency) | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-017 — No stop-market through the print` | documentation-only interpretive |
| N-018 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-018 — Scheduled vs unscheduled` | documentation-only interpretive |
| N-019 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-019 — CPI logic` | documentation-only interpretive |
| N-020 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-020 — NFP logic` | documentation-only interpretive |
| N-021 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-021 — Split data` | documentation-only interpretive |
| N-022 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-022 — Revisions` | documentation-only interpretive |
| N-023 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-023 — Decision vs presser` | documentation-only interpretive |
| N-024 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-024 — Buy rumor, sell fact` | documentation-only interpretive |
| N-025 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-025 — Zero surprise` | documentation-only interpretive |
| N-026 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-026 — PMI below 50` | documentation-only interpretive |
| N-027 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-027 — Ignore second-tier on CPI week` | documentation-only interpretive |
| N-028 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-028 — Yields disagree with the dollar` | documentation-only interpretive |
| N-029 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-029 — PPI as CPI preview` | documentation-only interpretive |
| N-030 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-030 — Absorption speed` | documentation-only interpretive |
| N-031 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-031 — Jobless claims spikes` | documentation-only interpretive |
| N-032 | INTERPRETIVE | INTERPRETIVE + FEATURE-05/09 | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-032 — Dovish keywords` | documentation-only interpretive |
| N-033 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-033 — FedWatch jump` | documentation-only interpretive |
| N-034 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-034 — Gold down with the dollar` | documentation-only interpretive |
| N-035 | DETERMINISTIC | DETERMINISTIC — `NEWS_VOID_SECONDS` / news operational freeze | `nanobot/trading/gates/news_operational.py` `evaluate_news_operational` `tests/trading/test_risk_gates.py::test_news_operational_freeze_and_void` | invoked from recommendation path; invoked from MT5 execution path |
| N-036 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-036 — Two-sided sweep bar` | documentation-only interpretive |
| N-037 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-037 — First M5 body as the map` | documentation-only interpretive |
| N-038 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-038 — Rejection-wick rule` | documentation-only interpretive |
| N-039 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-039 — News FVG` | documentation-only interpretive |
| N-040 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-040 — True break of the pre-news box` | documentation-only interpretive |
| N-041 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-041 — Immediate engulf of the spike` | documentation-only interpretive |
| N-042 | INTERPRETIVE | INTERPRETIVE (ADR chase DETERMINISTIC) | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-042 — No FOMO mid-bar` | documentation-only interpretive |
| N-043 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-043 — Tick-volume climax then death` | documentation-only interpretive |
| N-044 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-044 — Range reclaim after a sweep` | documentation-only interpretive |
| N-045 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-045 — No-wick follow-through` | documentation-only interpretive |
| N-046 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-046 — Asia high fake on the print` | documentation-only interpretive |
| N-047 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-047 — M1 is noise` | documentation-only interpretive |
| N-048 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-048 — Bollinger stretch` | documentation-only interpretive |
| N-049 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-049 — News-bar tail is the later stop` | documentation-only interpretive |
| N-050 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-050 — H1 trendline break on the print` | documentation-only interpretive |
| N-051 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-051 — Compression trap` | documentation-only interpretive |
| N-052 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-052 — Empty-volume support break` | documentation-only interpretive |
| N-053 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-053 — Giant news doji` | documentation-only interpretive |
| N-054 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-054 — First lower-low after a spike` | documentation-only interpretive |
| N-055 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-055 — Hold above the news high` | documentation-only interpretive |
| N-056 | DETERMINISTIC | DETERMINISTIC — spread guard / `SPREAD_MAX_POINTS` / `SPREAD_STABLE_SECONDS` | `nanobot/trading/gates/spread_guard.py` `evaluate_spread_guard` `tests/trading/test_risk_gates.py::test_spread_guard_blocks_wide_spread` | invoked from recommendation path; invoked from MT5 execution path |
| N-057 | DETERMINISTIC | DETERMINISTIC — slippage and latency / `SLIPPAGE_MAX_POINTS` | `nanobot/trading/gates/slippage_guard.py` `evaluate_slippage_guard` `tests/trading/test_risk_gates.py::test_margin_and_slippage` | invoked from recommendation path; invoked from MT5 execution path |
| N-058 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-058 — No martingale in the storm` | documentation-only interpretive |
| N-059 | DETERMINISTIC | DETERMINISTIC — `EXEC_LATENCY_MAX_MS` | `nanobot/trading/gates/slippage_guard.py` `evaluate_slippage_guard` `tests/trading/test_risk_gates.py::test_margin_and_slippage` | invoked from recommendation path; invoked from MT5 execution path |
| N-060 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-060 — Limits after the print, not markets` | documentation-only interpretive |
| N-061 | DETERMINISTIC | DETERMINISTIC — `EQUITY_SPIKE_PCT` | `nanobot/trading/gates/drawdown_breaker.py` `evaluate_drawdown_breaker` `tests/trading/test_risk_gates.py::test_equity_spike_breaker` | invoked from recommendation path; invoked from MT5 execution path |
| N-062 | DETERMINISTIC | DETERMINISTIC — `COOLDOWN_AFTER_NEWS_STOP_MINUTES` / cooldown lock | `nanobot/trading/gates/cooldown_lock.py` `evaluate_cooldown_lock` `tests/trading/test_risk_gates.py::test_cooldown_lock_blocks_while_active` | invoked from recommendation path; invoked from MT5 execution path |
| N-063 | DETERMINISTIC | DETERMINISTIC — `POST_NEWS_SL_BUFFER_POINTS` | `nanobot/trading/gates/trade_management.py` `management_snapshot` `tests/trading/test_risk_gates.py::test_trade_management_helpers` | invoked from MT5 execution path |
| N-064 | DETERMINISTIC | DETERMINISTIC — session and calendar lock rollover minutes, only with news/high-impact nearby | `nanobot/trading/gates/session_lock.py` `evaluate_session_lock` `tests/trading/test_risk_gates.py::test_session_rollover_only_near_news` | invoked from recommendation path; invoked from MT5 execution path |
| N-065 | DETERMINISTIC | DETERMINISTIC — same as P-193 / pending-order validity | `nanobot/trading/gates/pending_ttl.py` `evaluate_pending_ttl` `tests/trading/test_risk_gates.py::test_pending_ttl_and_half_distance` | invoked from recommendation path; invoked from MT5 execution path |
| N-066 | DETERMINISTIC | DETERMINISTIC — bad-tick filter / `BAD_TICK_POINTS` | `nanobot/trading/gates/bad_tick.py` `evaluate_bad_tick` `tests/trading/test_risk_gates.py::test_bad_tick` | invoked from recommendation path; invoked from MT5 execution path |
| N-067 | DETERMINISTIC | DETERMINISTIC — position sizing / `ATR_DOUBLE_LOT_HALVE` | `nanobot/trading/gates/position_sizing.py` `lot_from_balance` `tests/trading/test_risk_gates.py::test_position_sizing_dual_check` | invoked from recommendation path; invoked from MT5 execution path |
| N-068 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-068 — No blind fade of a shock` | documentation-only interpretive |
| N-069 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-069 — Windfall flatten` | documentation-only interpretive |
| N-070 | DETERMINISTIC | DETERMINISTIC — margin guard / `MARGIN_MIN_PCT` | `nanobot/trading/gates/margin_guard.py` `evaluate_margin_guard` `tests/trading/test_risk_gates.py::test_margin_and_slippage` | invoked from recommendation path; invoked from MT5 execution path |
| N-071 | DETERMINISTIC | DETERMINISTIC — `DISCONNECT_ALERT_SECONDS` | `nanobot/trading/gates/stale_quote.py` `evaluate_stale_quote` `tests/trading/test_risk_gates.py::test_stale_quote` | invoked from recommendation path; invoked from MT5 execution path |
| N-072 | INTERPRETIVE | INTERPRETIVE / execution implementation | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-072 — SL in the same packet as entry` | documentation-only interpretive |
| N-073 | DETERMINISTIC | DETERMINISTIC wait — `POST_NEWS_ENTRY_WAIT_MINUTES` / news and event shield after-window | `nanobot/trading/gates/news_operational.py` `evaluate_news_operational` `tests/trading/test_risk_gates.py::test_news_operational_freeze_and_void` | invoked from recommendation path; invoked from MT5 execution path |
| N-074 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-074 — Retest of the shock high/low` | documentation-only interpretive |
| N-075 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-075 — First H1 close after the print` | documentation-only interpretive |
| N-076 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-076 — OTE of the shock bar` | documentation-only interpretive |
| N-077 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-077 — NY continuation window` | documentation-only interpretive |
| N-078 | INTERPRETIVE | INTERPRETIVE using live partial split | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-078 — Scale out of news trends` | documentation-only interpretive |
| N-079 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-079 — Weekly break + news = swing` | documentation-only interpretive |
| N-080 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-080 — No new high after the shock` | documentation-only interpretive |
| N-081 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-081 — Engulf of the pullback` | documentation-only interpretive |
| N-082 | DETERMINISTIC | DETERMINISTIC — `ADR_CHASE_PCT` | `nanobot/trading/gates/adr_gap.py` `evaluate_adr_chase` `tests/trading/test_risk_gates.py::test_adr_and_gap_chase` | invoked from recommendation path; invoked from MT5 execution path |
| N-083 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-083 — Broken roof becomes the buy` | documentation-only interpretive |
| N-084 | INTERPRETIVE | INTERPRETIVE (except safe-haven) | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-084 — DXY must agree for gold longs` | documentation-only interpretive |
| N-085 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-085 — Broadening wedge after news` | documentation-only interpretive |
| N-086 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-086 — Post-data Fed speak` | documentation-only interpretive |
| N-087 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-087 — Wars cancel technical shorts` | documentation-only interpretive |
| N-088 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-088 — No shorting panic` | documentation-only interpretive |
| N-089 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-089 — First confirmed headline long` | documentation-only interpretive |
| N-090 | DETERMINISTIC | DETERMINISTIC — `GAP_NO_CHASE_POINTS` | `nanobot/trading/gates/adr_gap.py` `evaluate_gap_chase` `tests/trading/test_risk_gates.py::test_adr_and_gap_chase` | invoked from recommendation path; invoked from MT5 execution path |
| N-091 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-091 — Decouple from dollar and equities` | documentation-only interpretive |
| N-092 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-092 — Open extension targets` | documentation-only interpretive |
| N-093 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-093 — De-escalation invalidates` | documentation-only interpretive |
| N-094 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-094 — Bank-failure dip buys` | documentation-only interpretive |
| N-095 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-095 — Stop under the announcement bar` | documentation-only interpretive |
| N-096 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-096 — Media amplification trap` | documentation-only interpretive |
| N-097 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-097 — When non-traders buy gold on TV` | documentation-only interpretive |
| N-098 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-098 — News velocity` | documentation-only interpretive |
| N-099 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-099 — Straits and oil` | documentation-only interpretive |
| N-100 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-100.md` / `N-100 — Survive the storm` | documentation-only interpretive |
| C-001 | INTERPRETIVE | INTERPRETIVE time signature | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-001 — US 8:30 / 10:00` | documentation-only interpretive |
| C-002 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-002 — :45 flash PMI` | documentation-only interpretive |
| C-003 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-003 — FOMC 14:00 ET` | documentation-only interpretive |
| C-004 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-004 — Presser 14:30 ET` | documentation-only interpretive |
| C-005 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-005 — NFP first Friday 8:30 ET` | documentation-only interpretive |
| C-006 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-006 — London open UK data` | documentation-only interpretive |
| C-007 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-007 — London PM gold fix` | documentation-only interpretive |
| C-008 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-008 — Treasury auctions 13:00 ET` | documentation-only interpretive |
| C-009 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-009 — OpEx / futures expiry Friday` | documentation-only interpretive |
| C-010 | INTERPRETIVE | INTERPRETIVE (news and event shield uses calendar timestamps) | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-010 — API sync < 60s` | documentation-only interpretive |
| C-011 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-011 — EIA / oil 10:30 ET Wednesday` | documentation-only interpretive |
| C-012 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-012 — ECB Thursday 14:15 CET` | documentation-only interpretive |
| C-013 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-013 — OPEC` | documentation-only interpretive |
| C-014 | INTERPRETIVE | INTERPRETIVE + FEATURE-03/05 | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-014 — Unscheduled chair TV` | documentation-only interpretive |
| C-015 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-015 — Quarter-end last 30 minutes` | documentation-only interpretive |
| C-016 | DETERMINISTIC | DETERMINISTIC — `NEWS_CANDLE_ATR_MULT` | `nanobot/trading/gates/news_candle.py` `evaluate_news_candle_shield` `tests/trading/test_risk_gates.py::test_news_candle_and_emergency_burst` | invoked from recommendation path; invoked from MT5 execution path |
| C-017 | DETERMINISTIC | DETERMINISTIC — `NEWS_CANDLE_M1_POINTS` | `nanobot/trading/gates/news_candle.py` `is_news_candle` `tests/trading/test_risk_gates.py::test_news_candle_and_emergency_burst` | invoked from recommendation path; invoked from MT5 execution path |
| C-018 | DETERMINISTIC | DETERMINISTIC — `NEWS_CANDLE_M5_ADR_FRACTION` | `nanobot/trading/gates/news_candle.py` `is_news_candle` `tests/trading/test_risk_gates.py::test_news_candle_and_emergency_burst` | invoked from recommendation path; invoked from MT5 execution path |
| C-019 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-019 — Velocity` | documentation-only interpretive |
| C-020 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-020 — Current bar = last ten combined` | documentation-only interpretive |
| C-021 | INTERPRETIVE | INTERPRETIVE (bad tick bad-tick filter) | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-021 — Hidden gap inside the bar` | documentation-only interpretive |
| C-022 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-022 — >3.5σ Bollinger close` | documentation-only interpretive |
| C-023 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-023 — One H1 eats three days` | documentation-only interpretive |
| C-024 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-024 — Spike then freeze` | documentation-only interpretive |
| C-025 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-025 — Expanding 1x-2x-4x M5s` | documentation-only interpretive |
| C-026 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-026 — Coil then giant` | documentation-only interpretive |
| C-027 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-027 — PDH and PDL in one M15` | documentation-only interpretive |
| C-028 | INTERPRETIVE | INTERPRETIVE using live point math | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-028 — Full-body 120+ point M5 marubozu` | documentation-only interpretive |
| C-029 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-029 — 80% give-back in the same bar` | documentation-only interpretive |
| C-030 | INTERPRETIVE | INTERPRETIVE (volume z is DETERMINISTIC C-031) | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-030 — Range z-score > 4` | documentation-only interpretive |
| C-031 | DETERMINISTIC | DETERMINISTIC — `NEWS_CANDLE_VOLUME_Z` | `nanobot/trading/gates/news_candle.py` `is_news_candle` `tests/trading/test_risk_gates.py::test_news_candle_and_emergency_burst` | invoked from recommendation path; invoked from MT5 execution path |
| C-032 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-032 — Tick frequency spike` | documentation-only interpretive |
| C-033 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-033 — Front-loaded climax` | documentation-only interpretive |
| C-034 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-034 — M1 volume = quiet H1` | documentation-only interpretive |
| C-035 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-035 — No 5ms gaps between ticks` | documentation-only interpretive |
| C-036 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-036 — Buy volume at the low of a red spike` | documentation-only interpretive |
| C-037 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-037 — One bar = 25% of the session` | documentation-only interpretive |
| C-038 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-038 — Price up, next bars' volume down` | documentation-only interpretive |
| C-039 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-039 — Session max ticks at a break` | documentation-only interpretive |
| C-040 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-040 — 90% one-sided delta` | documentation-only interpretive |
| C-041 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-041 — Ask evaporation` | documentation-only interpretive |
| C-042 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-042 — Same-minute vs history` | documentation-only interpretive |
| C-043 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-043 — Ticks piled on the wick` | documentation-only interpretive |
| C-044 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-044 — Two-second freeze then 200 ticks` | documentation-only interpretive |
| C-045 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-045 — Huge slip on low ticks` | documentation-only interpretive |
| C-046 | DETERMINISTIC | DETERMINISTIC overlap with spread guard / pre-news multiplier | `nanobot/trading/gates/spread_guard.py` `evaluate_spread_guard` `tests/trading/test_risk_gates.py::test_spread_guard_blocks_wide_spread` | invoked from recommendation path; invoked from MT5 execution path |
| C-047 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-047 — Pumping spread` | documentation-only interpretive |
| C-048 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-048 — Wide spread into a green rocket` | documentation-only interpretive |
| C-049 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-049 — Bid/ask freeze asymmetry` | documentation-only interpretive |
| C-050 | DETERMINISTIC | DETERMINISTIC — `SLIPPAGE_PROBE_POINTS` | `nanobot/trading/gates/slippage_guard.py` `evaluate_slippage_guard` `tests/trading/test_risk_gates.py::test_margin_and_slippage` | invoked from recommendation path; invoked from MT5 execution path |
| C-051 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-051 — DOM cleared` | documentation-only interpretive |
| C-052 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-052 — Spread widens 10s before price` | documentation-only interpretive |
| C-053 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-053 — Gap ticks` | documentation-only interpretive |
| C-054 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-054 — Mid-NY spread blowout` | documentation-only interpretive |
| C-055 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-055 — Spread-wick trap at resistance` | documentation-only interpretive |
| C-056 | DETERMINISTIC | DETERMINISTIC overlap with `SPREAD_STABLE_SECONDS` | `nanobot/trading/gates/spread_guard.py` `evaluate_spread_guard` `tests/trading/test_risk_gates.py::test_spread_guard_blocks_wide_spread` | invoked from recommendation path; invoked from MT5 execution path |
| C-057 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-057 — Gold spread vs EURUSD` | documentation-only interpretive |
| C-058 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-058 — Ask-only ATH` | documentation-only interpretive |
| C-059 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-059 — Straight-line vacuum dump` | documentation-only interpretive |
| C-060 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-060 — Wide spread, tiny range, before a speech` | documentation-only interpretive |
| C-061 | INTERPRETIVE | INTERPRETIVE + FEATURE-10 | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-061 — DXY mirror` | documentation-only interpretive |
| C-062 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-062 — US10Y shock` | documentation-only interpretive |
| C-063 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-063 — Silver 95% sync` | documentation-only interpretive |
| C-064 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-064 — Decoupling rocket` | documentation-only interpretive |
| C-065 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-065 — Risk-off ES dump` | documentation-only interpretive |
| C-066 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-066 — Brent sync` | documentation-only interpretive |
| C-067 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-067 — USDJPY flash` | documentation-only interpretive |
| C-068 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-068 — Copper split` | documentation-only interpretive |
| C-069 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-069 — VIX +5%` | documentation-only interpretive |
| C-070 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-070 — CHF/JPY haven stack` | documentation-only interpretive |
| C-071 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-071 — FX intervention` | documentation-only interpretive |
| C-072 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-072 — Crypto dump, gold up` | documentation-only interpretive |
| C-073 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-073 — XAUEUR confirms` | documentation-only interpretive |
| C-074 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-074 — TIPS breakdown` | documentation-only interpretive |
| C-075 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-075 — EURUSD leads by 10s` | documentation-only interpretive |
| C-076 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-076 — Expanding horn` | documentation-only interpretive |
| C-077 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-077 — Engulfing flush` | documentation-only interpretive |
| C-078 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-078 — Exhaustion pin` | documentation-only interpretive |
| C-079 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-079 — Shadowless run` | documentation-only interpretive |
| C-080 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-080 — Tower / imbalance` | documentation-only interpretive |
| C-081 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-081 — Outside-bar vs last five` | documentation-only interpretive |
| C-082 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-082 — V-reversal pair` | documentation-only interpretive |
| C-083 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-083 — Full close beyond resistance, no upper wick` | documentation-only interpretive |
| C-084 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-084 — Three same-size M5s` | documentation-only interpretive |
| C-085 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-085 — One bar breaks slant + flat + fib` | documentation-only interpretive |
| C-086 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-086 — Super-sized doji` | documentation-only interpretive |
| C-087 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-087 — Fake hang then collapse` | documentation-only interpretive |
| C-088 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-088 — Intraday breakaway gap` | documentation-only interpretive |
| C-089 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-089 — Asia range eaten at NY open` | documentation-only interpretive |
| C-090 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-090 — H4 marubozu from stacked news` | documentation-only interpretive |
| C-091 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-091 — Asian midnight flash` | documentation-only interpretive |
| C-092 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-092 — CME halt shadow` | documentation-only interpretive |
| C-093 | DETERMINISTIC | DETERMINISTIC overlap with N-090 | `nanobot/trading/gates/adr_gap.py` `evaluate_gap_chase` `tests/trading/test_risk_gates.py::test_adr_and_gap_chase` | invoked from recommendation path; invoked from MT5 execution path |
| C-094 | INTERPRETIVE | INTERPRETIVE + FEATURE-05 | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-094 — Strike / strait headline bar` | documentation-only interpretive |
| C-095 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-095 — Silent coil then 80-point bar, empty calendar` | documentation-only interpretive |
| C-096 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-096 — Tariffs / sanctions bar` | documentation-only interpretive |
| C-097 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-097 — Regional-bank panic buy` | documentation-only interpretive |
| C-098 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-098 — De-escalation dump bar` | documentation-only interpretive |
| C-099 | INTERPRETIVE | INTERPRETIVE | `nanobot/skills/news-volatility-protocol/references/news-candles-100.md` / `C-099 — US downgrade bar` | documentation-only interpretive |
| C-100 | DETERMINISTIC | DETERMINISTIC combo — ATR multiple + volume z + spread blowout | `nanobot/trading/gates/news_candle.py` `evaluate_news_candle_shield` `tests/trading/test_risk_gates.py::test_news_candle_and_emergency_burst` | invoked from recommendation path; invoked from MT5 execution path |

## FEATURE-01 … FEATURE-10

| Id | Class | Module | Tool / call | Test | Honesty |
| --- | --- | --- | --- | --- | --- |
| FEATURE-01 | DETERMINISTIC engine | `nanobot/trading/intel/telegram_scraper.py` | `gold_intel_scan` / `fetch_recent` | `tests/trading/test_intel_engines.py::test_telegram_probe_without_credentials` | inactive unless Telethon + credentials |
| FEATURE-02 | DETERMINISTIC engine | `nanobot/trading/intel/rss_aggregator.py` | `gold_intel_scan` / `fetch_rss_headlines` | `tests/trading/test_intel_engines.py::test_rss_parse_feed_body_without_network` | empty list if feedparser missing |
| FEATURE-03 | DETERMINISTIC engine | `nanobot/trading/intel/vip_tracker.py` | `gold_intel_scan` / `fetch_vip_statements` | `tests/trading/test_intel_engines.py::test_vip_impact_marks_fed_high` | Nitter RSS via FEATURE-02 |
| FEATURE-04 | DETERMINISTIC engine | `nanobot/trading/intel/calendar_scraper.py` | `gold_intel_scan` / `fetch_economic_calendar` | `tests/trading/test_intel_engines.py::test_calendar_json_surprise` | parser works offline; fetch is network |
| FEATURE-05 | DETERMINISTIC engine | `nanobot/trading/intel/regex_emergency.py` | `gold_intel_scan` / `scan_emergency` | `tests/trading/test_intel_engines.py::test_regex_emergency_war_and_lock` | always on |
| FEATURE-06 | DETERMINISTIC engine | `nanobot/trading/intel/vector_playbook.py` | `gold_intel_scan` | `tests/trading/test_intel_engines.py::test_vector_playbook_ranks_similar_context` | `backend=bag_of_words` unless Chroma present |
| FEATURE-07 | DETERMINISTIC engine | `nanobot/trading/intel/dtw_matcher.py` | `gold_intel_scan` / `match_pattern` | `tests/trading/test_intel_engines.py::test_dtw_picks_a_template` | `backend=builtin_dp` unless fastdtw present |
| FEATURE-08 | DETERMINISTIC engine | `nanobot/trading/intel/postmortem.py` | recommendation path / `refuse_repeat_error` | `tests/trading/test_intel_engines.py::test_postmortem_repeat_detection` | sqlite3 always |
| FEATURE-09 | DETERMINISTIC engine | `nanobot/trading/intel/local_sentiment.py` | `gold_intel_scan` / `classify_sentiment` | `tests/trading/test_intel_engines.py::test_sentiment_fallback_hawkish` | `source=fallback` unless Ollama answers |
| FEATURE-10 | DETERMINISTIC engine | `nanobot/trading/intel/intermarket.py` | `gold_intel_scan` / `intermarket_snapshot` | `tests/trading/test_intel_engines.py::test_intermarket_divergence_and_override` | `source=unavailable` without yfinance/MT5/overrides |

## EXCLUDED

| Id | Reason |
| --- | --- |
| P-182 | Conflicts with mandatory HITL propose → confirm |
| Section 5.2 Quick historical replay | Backtest / historical candle replay is excluded |
| Paid APIs | Spec allows free engines only; MetaAPI is the documented optional exception |

