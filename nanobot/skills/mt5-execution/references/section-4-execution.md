# Spec section 4 — Execution and trade management

Table of contents: `S4.1` MT5 · `S4.2` Trail · `S4.3` Breakeven · `S4.4` Partials · `S4.5` News shield · `S4.6` Early exit

HITL propose→confirm wraps every send/modify/close. Playbook 182 is excluded.

### S4.1 — Direct MT5 via MetaAPI

Market and pending (limit/stop) go through MetaAPI after confirm. Rec path still never sends. Proposal TTL is `live().PROPOSAL_TTL_SECONDS`. Stale quotes, ping, and exec latency are DETERMINISTIC (G13, G19).

### S4.2 — Trailing stop

INTERPRETIVE trail behind structure or ATR multiple. The multiple is `live().TRAIL_ATR_MULT`. Disable tight trails into a print (N-008). Chandelier-style trail (P-042) is judgment using live ATR.

### S4.3 — Auto breakeven

Move stop to entry only after price travels the live breakeven RR **and** a new M15 swing exists (P-038). Early BE gets wicked out (P-046).

### S4.4 — Partial take profit

Live fractions: TP1 / TP2 / remainder (`PARTIAL_TP1_FRACTION`, `PARTIAL_TP2_FRACTION`, or `PARTIAL_TP_SPLIT`). INTERPRETIVE: skip flattening the runner on a marubozu into TP1 (P-142).

### S4.5 — News shield

DETERMINISTIC: cancel pendings and flatten-near-entry / BE remaining size inside the live news-shield minutes (G17). INTERPRETIVE: warn the operator ten minutes out in their language.

### S4.6 — Early exit on momentum death

INTERPRETIVE: if strong reversal candles or fading range appear before TP/SL, recommend (or propose) an immediate exit. Two M5 closes against with rising momentum can justify leaving before the structural stop (P-045).
