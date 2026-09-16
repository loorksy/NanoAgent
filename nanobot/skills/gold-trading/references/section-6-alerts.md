# Spec section 6 — Alerts and operator interface

Table of contents: `S6.1` Chart ping · `S6.2` HITL buttons · `S6.3` Morning brief · `S6.4` PnL reports · `S6.5` Natural questions · `S6.6` Feed death · `S6.7` Multi-channel fan-out

Follow `trading-proactive` for when to speak. This file is the spec-6 map only.

### S6.1 — Instant chart with levels
Send a captured chart with entry, stop, targets, and the INTERPRETIVE why. Prefer one artifact over spam.

### S6.2 — Human confirm
Recommendations may include approve/ignore. MT5 sends wait for that confirm. Not a Risk Parameters toggle.

### S6.3 — London/NY morning brief
If the operator opted in, send a short pre-session note: liquidity, prior highs/lows, pivots. No forced trade.

### S6.4 — Daily/weekly scorecard
Win rate, realized R, max DD — from stores, never invented.

### S6.5 — Natural-language gold questions
Answer from tools. Copy `display.*` prices verbatim.

### S6.6 — Stale feed alert
DETERMINISTIC disconnect/stale seconds. Tell the operator the feed is dead; do not hallucinate ticks.

### S6.7 — Fan-out
Telegram + WebUI (and other configured channels) get the same update. No staggered "exclusive" calls.
