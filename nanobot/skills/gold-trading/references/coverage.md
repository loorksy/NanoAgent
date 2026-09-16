# Gold encyclopedia coverage

Grep this table by spec id (`S3.6`, `P-182`, `N-056`, `C-016`). DETERMINISTIC numbers live in `policy.live()` / gates. Skills are English; operator copy stays in `nanobot/trading/i18n.py`.

## Spec sections 1–9

| Id | Kind | Skill / reference | Gate / engine |
| --- | --- | --- | --- |
| S1.1–S1.7 | INTERPRETIVE | `technical-analysis` / `section-1-price-action.md` | G2 G3 G4 G6 (shape only) |
| S2.1–S2.4 | INTERPRETIVE | `macro-radar` / `section-2-macro.md` | FEATURE-01…05, 09, 10; G1 timestamps |
| S3.1 | DETERMINISTIC | `risk-guardrails` | G20 |
| S3.2 | DETERMINISTIC | `risk-guardrails` | G12 |
| S3.3 | DETERMINISTIC | `risk-guardrails` | G9 |
| S3.4 | DETERMINISTIC | `risk-guardrails` | G10 |
| S3.5 | DETERMINISTIC | `risk-guardrails` | G11 |
| S3.6 | DETERMINISTIC | `risk-guardrails` | G8 |
| S4.1–S4.6 | MIXED | `mt5-execution` / `section-4-execution.md` | HITL; G13 G17 G19 |
| S5.1–S5.5 | INTERPRETIVE | `memory-review` / `section-5-memory.md` | FEATURE-06 07 08 |
| S6.1–S6.7 | INTERPRETIVE | `gold-trading` / `section-6-alerts.md` | `trading-proactive`; G13 alert |
| S7.1–S7.5 | MIXED | `security-resilience` | kill switch; G16 |
| S8.1–S8.5 | INTERPRETIVE | `multi-tasking-scenarios` | one live card; toggles skip gates, never confirm |
| S9.1–S9.4 | INTERPRETIVE | `gold-trading` / `section-9-behavior.md` + `SOUL.md` | — |

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

DETERMINISTIC cluster: N-001…005, 010, 011, 016, 035, 056, 057, 059, 061–067, 070, 071, 073, 082, 090 (plus G1 stricter than N-001).

## Candles C-001 … C-100

File: `news-volatility-protocol/references/news-candles-100.md`

DETERMINISTIC cluster: C-016, C-017, C-018, C-031, C-046/C-050/C-056 overlap, C-093/N-090, **C-100 triple**.

## FEATURE-01 … 10

| Id | Module |
| --- | --- |
| 01 Telegram | `nanobot/trading/intel/telegram_scraper.py` |
| 02 RSS | `rss_aggregator.py` |
| 03 VIP/Nitter | `vip_tracker.py` |
| 04 Calendar | `calendar_scraper.py` |
| 05 Regex emergency | `regex_emergency.py` |
| 06 Vector playbook | `vector_playbook.py` |
| 07 FastDTW | `dtw_matcher.py` |
| 08 Post-mortem | `postmortem.py` |
| 09 Ollama sentiment | `local_sentiment.py` |
| 10 Intermarket | `intermarket.py` |
