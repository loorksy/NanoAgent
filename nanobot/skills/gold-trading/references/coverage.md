# Gold encyclopedia coverage

| Original rule range | This file | Deterministic destinations | Interpretive headings |
| --- | --- | --- | --- |
| P-001 … P-200 / N-001 … N-100 / C-001 … C-100 / FEATURE-01 … 10 | `coverage.md` | per-rule rows in `spec-coverage.md` | per-rule rows in `spec-coverage.md` |

Grep this table by capability name (`Minimum reward-to-risk`, `P-182`, `N-056`, `C-016`). DETERMINISTIC numbers live in `policy.live()` / gates. Skills are English; operator copy stays in `nanobot/trading/i18n.py`. Full per-rule destinations: [spec-coverage.md](spec-coverage.md).

## Capability map

| Capability | Kind | Skill / reference | Gate / engine |
| --- | --- | --- | --- |
| Technical and price action | MIXED | `technical-analysis` / `section-1-price-action.md` | plan alignment / structure / entry shape; FVG, Fibonacci, RSI/MACD, CHoCH detectors feed geometry evidence |
| Macro radar | INTERPRETIVE | `macro-radar` / `section-2-macro.md` | Telegram, RSS, VIP, calendar, regex, sentiment, intermarket; news-window timestamps |
| Automatic lot sizing | DETERMINISTIC | `risk-guardrails` | position sizing |
| Daily drawdown breaker | DETERMINISTIC | `risk-guardrails` | daily drawdown breaker |
| Spread guard | DETERMINISTIC | `risk-guardrails` | spread guard |
| Cooldown lock | DETERMINISTIC | `risk-guardrails` | cooldown lock |
| Maximum open positions | DETERMINISTIC | `risk-guardrails` | max positions |
| Minimum reward-to-risk | DETERMINISTIC | `risk-guardrails` | reward-to-risk filter |
| Execution and trade management | MIXED | `mt5-execution` / `section-4-execution.md` | HITL; stale quote, news operational, slippage; time-stop + no-widen on modify |
| Similar cases, post-trade, lesson log, dual review | INTERPRETIVE | `memory-review` / `section-5-memory.md` | vector playbook, FastDTW, post-mortem queried before a new rec |
| Quick historical replay | EXCLUDED | backtest / historical candle replay | FastDTW is live-chart only |
| Alerts and operator interface | INTERPRETIVE | `gold-trading` / `section-6-alerts.md` | `trading-proactive`; stale-quote alert |
| Security and resilience | MIXED | `security-resilience` | kill switch; bad-tick filter; ticket SQLite restore; flatten HITL; adopt candidates |
| Multi-tasking and scenarios | INTERPRETIVE | `multi-tasking-scenarios` | one live card; WebUI toggles skip gates, never confirm |
| Behavioral alignment | INTERPRETIVE | `gold-trading` / `section-9-behavior.md` + `SOUL.md` | — |

## Playbook P-001 … P-200

| Range | File | Notes |
| --- | --- | --- |
| P-001–025 | `xauusd-playbook/references/playbook-001-025-entry.md` | P-012 stale hours DETERMINISTIC |
| P-026–055 | `playbook-026-055-stops.md` | P-029 036 038 039 047 052 DETERMINISTIC pieces |
| P-056–080 | `playbook-056-080-retest.md` | INTERPRETIVE |
| P-081–105 | `playbook-081-105-trendlines.md` | INTERPRETIVE |
| P-106–135 | `playbook-106-135-gold-liquidity.md` | P-118 127 134 DETERMINISTIC |
| P-136–160 | `playbook-136-160-targets.md` | P-137 149 153 DETERMINISTIC pieces |
| P-161–180 | `playbook-161-180-candle-traps.md` | INTERPRETIVE |
| P-181–200 | `playbook-181-200-discipline.md` | **P-182 EXCLUDED (HITL)**; P-183 185–189 191 193 195–197 199 DETERMINISTIC |

## News N-001 … N-100

File: `news-volatility-protocol/references/news-100.md`

DETERMINISTIC cluster: N-001…005, 010, 011, 016, 035, 056, 057, 059, 061–067, 070, 071, 073, 082, 090 (news window is stricter than the fifteen-minute freeze).

## Candles C-001 … C-100

File: `news-volatility-protocol/references/news-candles-100.md`

DETERMINISTIC cluster: C-016, C-017, C-018, C-031, C-046/C-050/C-056 overlap, C-093/N-090, **C-100 triple**.

## FEATURE-01 … 10

| Id | Module |
| --- | --- |
| 01 Telegram | `telegram_scraper.py` + `gold_intel_scan` readiness probe |
| 02 RSS | `rss_aggregator.py` |
| 03 VIP/Nitter | `vip_tracker.py` |
| 04 Calendar | `calendar_scraper.py` |
| 05 Regex emergency | `regex_emergency.py` |
| 06 Vector playbook | `vector_playbook.py` |
| 07 FastDTW | `dtw_matcher.py` |
| 08 Post-mortem | `postmortem.py` — queried before a new buy/sell rec |
| 09 Ollama sentiment | `local_sentiment.py` |
| 10 Intermarket | `intermarket.py` |
