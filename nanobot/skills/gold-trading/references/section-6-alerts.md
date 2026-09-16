# Alerts and operator interface

Table of contents: Instant chart with levels · Human confirm · London/NY morning brief · Daily/weekly scorecard · Natural-language gold questions · Stale feed alert · Multi-channel fan-out

Follow `trading-proactive` for when to speak. This file is the alerts map only.

### Instant chart with levels
Send a captured chart with entry, stop, targets, and the INTERPRETIVE why. Prefer one artifact over spam.

### Human confirm
Recommendations may include approve/ignore. MT5 sends wait for that confirm. Not a Risk Parameters toggle.

### London/NY morning brief
If the operator opted in, send a short pre-session note: liquidity, prior highs/lows, pivots. No forced trade.

### Daily/weekly scorecard
Win rate, realized reward-to-risk, max drawdown — from stores, never invented.

### Natural-language gold questions
Answer from tools. Copy `display.*` prices verbatim.

### Stale feed alert
DETERMINISTIC disconnect/stale seconds. Tell the operator the feed is dead; do not hallucinate ticks.

### Fan-out
Telegram + WebUI (and other configured channels) get the same update. No staggered "exclusive" calls.
