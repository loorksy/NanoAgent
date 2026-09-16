---
name: macro-radar
description: Gold macro radar — economic calendar surprise, DXY confluence, hawkish/dovish central-bank tone, and geopolitical safe-haven headlines. Use when news, CPI, NFP, FOMC, yields, dollar, or war/risk-off drive the gold question. English skill; reply in the operator's language.
---

# Macro radar (gold)

INTERPRETIVE skill. Calendar blackout minutes, news-day risk, and freeze windows are DETERMINISTIC — read `policy.live()` / gates, never a memorized clock.

## References

- Macro radar: [references/section-2-macro.md](references/section-2-macro.md)
- News protocols: `nanobot/skills/news-volatility-protocol/references/news-100.md` (`N-001` …)
- Free engines: FEATURE-01…05, 09, 10 (Telegram, RSS, VIP, calendar, regex, sentiment, intermarket)

## Steps

1. Separate scheduled red-folder data from unscheduled geopolitics. The regex emergency engine fires first; sentiment is a weight, not a veto.
2. Treat DXY confirmation as confluence, not a sacred inverse (playbook 111, news 91). Bank-panic and war can lift gold with the dollar.
3. After a print, wait for the DETERMINISTIC void/blackout to clear, then judge surprise, revisions, and press-conference tone.
4. Never publish a new recommendation inside a news freeze. If a gate vetoes, say which user-facing check refused — never a raw gate id.

## Output

- Macro bias for gold (bullish / bearish / conflicted).
- Whether the driver is data, yields, dollar, or safe-haven.
- Whether the operator must wait (freeze) or may analyze (post-print structure).

## Example

Operator: "NFP in twenty minutes, buy?"
You: "No new plan until the high-impact window clears. After the first M15 close, we read surprise plus dollar confirmation — not the first tick."

## Do not

- Short gold into a confirmed geopolitical panic (news 88) on RSI alone.
- Invent actual-vs-forecast numbers. Use calendar/tool output.
- Disable human confirmation to "catch the spike."
