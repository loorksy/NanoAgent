# Execution and trade management

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| section-4-execution | `section-4-execution.md` | — | section narrative |


Table of contents: Direct MetaTrader 5 · Trailing stop · Auto breakeven · Partial take profit · News shield · Early exit

HITL propose→confirm wraps every send/modify/close. Playbook 182 is excluded.

### Direct MT5 via MetaAPI

Market and pending (limit/stop) go through MetaAPI after confirm. Rec path still never sends. Proposal TTL is `live().PROPOSAL_TTL_SECONDS`. Stale quotes, ping, and exec latency are DETERMINISTIC (stale-quote guard, slippage guard).

### Trailing stop

INTERPRETIVE trail behind structure or ATR multiple. The multiple is `live().TRAIL_ATR_MULT`. Disable tight trails into a print (N-008). Chandelier-style trail (P-042) is judgment using live ATR.

### Auto breakeven

Move stop to entry only after price travels the live breakeven reward-to-risk **and** a new M15 swing exists (P-038). Early BE gets wicked out (P-046).

### Partial take profit

Live fractions: TP1 / TP2 / remainder (`PARTIAL_TP1_FRACTION`, `PARTIAL_TP2_FRACTION`, or `PARTIAL_TP_SPLIT`). INTERPRETIVE: skip flattening the runner on a marubozu into TP1 (P-142).

### News shield

DETERMINISTIC: cancel pendings and flatten-near-entry / BE remaining size inside the live news-shield minutes (news operational). INTERPRETIVE: warn the operator ten minutes out in their language.

### Early exit on momentum death

INTERPRETIVE: if strong reversal candles or fading range appear before TP/SL, recommend (or propose) an immediate exit. Two M5 closes against with rising momentum can justify leaving before the structural stop (P-045).
