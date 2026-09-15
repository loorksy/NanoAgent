---
name: gold-execution-discipline
description: XAUUSD algorithmic execution and discipline field rules (181-200). Use for zero-hesitation sends, pending TTL, no revenge trading, dual magic numbers, stale quotes, holidays, and capital-first priority.
---

# Gold Execution Discipline Rules (181-200)

## Rules

181. **Standing aside is a trade:** When signals conflict and clarity is gone, flat is a profitable capital-protecting decision.
182. **Zero-hesitation execution:** Once algorithmic conditions are true and grants allow, send immediately — do not wait for late human second-guessing (unless chat grant is `ask`, which requires Approve first).
183. **Auto-cancel stale pendings:** Any buy/sell limit/stop unfilled for 3 hours is cancelled — context expired.
184. **No double-down on same side loser:** Ban opening a new gold long while a prior losing long is still open (no loss stacking).
185. **Separate scalp vs swing magic numbers:** Each strategy has its own magic number; never merge a scalp stop with a swing stop.
186. **Unscheduled 80-point spike:** If gold moves ~80 points in one minute with no technical cause and no calendar event, flatten immediately — likely news leak.
187. **Revenge freeze:** After two consecutive losses in the same session, freeze new entries for 60 minutes (extendable via settings cooldown).
188. **Double-check lot math:** Recompute lot size twice in code before send so a decimal error cannot blow the account.
189. **Fresh tick before send:** If the last MT5/MetaAPI tick is older than 5 seconds, abort — suspect disconnect.
190. **No bias lock:** If structure breaks against the bias, drop the prior narrative immediately — market is right.
191. **Daily max loss halt:** At configured daily drawdown (default 3%), flatten all and disconnect trading until next day.
192. **Market orders on hard confirmation:** Prefer market over limit when a confirmed break candle exists so you catch the train.
193. **Cancel if price already ran half to TP:** If price travels ~50% to target before the pending fills, delete the pending — do not chase the return.
194. **Comment the thesis code:** Write the setup code into the order comment (e.g. `BOS_M15_FVG_Retest`) for later review.
195. **No new entries last 15 minutes of day:** End-of-day liquidity is thin; swap/spread costs rise.
196. **Live R:R recompute:** If price drifts one point worse than planned entry and R:R falls below 1:1.5 (or configured floor), cancel.
197. **Holiday blackout:** Fully disable the algo on major holidays (New Year, Thanksgiving, etc.) when primary market makers are absent.
198. **Kill TF contradictions:** If H4 is explicit long while M15 shows a completed distribution short pattern, ban entry until frames agree.
199. **Lot scales on balance, not floating equity:** Increase size from closed balance growth, never from unrealized equity spikes.
200. **Golden rule:** The market is always right; technical analysis is a probability map. Protect capital first; profits second.
