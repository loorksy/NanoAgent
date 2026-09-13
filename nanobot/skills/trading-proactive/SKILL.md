---
name: trading-proactive
description: Intelligent proactive gold-trading communication — when to speak, when to stay silent, market-hours honesty, and user-requested watches via cron or HEARTBEAT. Use for Telegram/WhatsApp notifications, scheduled briefings, holiday/closed-market replies, outcome alerts, or when the user asks to be notified about news, open trades, or unusual conditions.
---

# Trading Proactive Communication

## Core rule

**You decide when to notify — not fixed background bots.**

Do not spam the operator with repetitive scanner notes, "still active" reminders, or compressed-range boilerplate. Proactive messages must pass a **notification gate** (below). Silence is correct when there is nothing new, actionable, or explicitly requested.

Background gold cron jobs (`gold_scan`, `gold_news`, `gold_rec_followup`) are **off by default**. Only enable them when the operator explicitly asks for automatic periodic monitoring and accepts the schedule.

## Notification gate

Send a proactive outbound message **only if all** apply:

1. **Material** — new information, a state change, or a deadline the user cares about (not a repeat of the last message).
2. **Actionable or explicitly requested** — helps the user decide, confirms a scheduled briefing, or fulfills a watch they asked for.
3. **Right channel & time** — respect quiet hours and market session when possible.
4. **Deduplicated** — never resend the same summary every 15–30 minutes.

If the gate fails → **stay silent** (or answer only inside the current chat turn when the user spoke first).

## Market closed / holiday honesty

When the user asks for a **recommendation** but the market is closed (weekend, holiday, or no fresh XAUUSD liquidity):

1. Say clearly that **today is closed / there is no live tradeable session** — no fake recommendation.
2. Offer **one concrete next step**, e.g. notify at session open + short news brief.
3. If they accept → create a **one-time or recurring cron** (or HEARTBEAT task) with exact time and timezone; confirm in their language using their name when known.

**Example (Arabic):**

> والله اليوم عطلة والسوق مسكّر، ما في توصية حيّة. تحب أرسلك إشعار أول ما يفتح السوق وموجز الأخبار؟

If yes:

> طيب يا {name}، تم — راح يصلك إشعار أول ما يفتح السوق الساعة {time} ({tz}).

Use `get_gold_quote` / session context to sanity-check; do not invent open hours.

## User-requested watches (normal + unusual)

When the operator asks for monitoring — including unusual requests — **you** create the task:

| User intent | Tool | Notes |
|-------------|------|-------|
| Remind at a specific time | `cron` `at=` | One-shot market open briefing |
| Repeat check (news, levels, open trade) | `cron` `every_seconds` / `cron_expr` | Message should describe *what to evaluate*, not a canned spam string |
| Background check, notify only on change | `HEARTBEAT.md` | Edit Active Tasks; remove when done |
| Sudden news → pause trading alert | `cron` or HEARTBEAT | Task: run news macro; alert only if high-impact + tradability blocked |

**Examples:**

- «لو صار خبر فجأة وتحس لازم أوقف التداول خبرني» → add cron/heartbeat: check news risk; notify only on escalation to high + actionable headline; include suggested stand-aside line.
- «ذكرني بتوصيتي إذا وصل TP1» → prefer outcome pipeline on transition; do **not** poll "still active" every 15 minutes.

Always **confirm** what was scheduled, when it fires, and how to cancel (`cron action="list"` / remove job / delete HEARTBEAT line).

## What not to do

- Do **not** register or assume default `gold_scan` / `gold_rec_followup` jobs unless the user opted in.
- Do **not** send English boilerplate like `Gold scanner: Bot note: compressed range` without user context.
- Do **not** repeat `Open gold SELL still active` on a timer — status updates only on **real transitions** (entered trade, TP1, invalidated) or when the user asks.
- Do **not** add standing HEARTBEAT tasks that re-summarize the same live recommendation every cycle.

## Outcome alerts (when enabled)

Legitimate proactive alerts for open recommendations:

- First entry into trade (`in_trade`)
- TP1 hit
- Plan invalidated (stop)

One alert per transition per recommendation. No re-alerts for oscillation around entry.

## Artifacts over noise

Prefer **one rich artifact** (chart snapshot, level table, news brief) over many short duplicate texts. See `gold-trading` skill and `docs/designs/gold-trading-roadmap.md` Phase G.

## Config reference

Operators may opt into legacy periodic monitors:

```json
"gateway": {
  "tradingCron": { "enabled": true }
}
```

Default is `false`. Recommend keeping it false unless they understand the trade-off.

## Quick checklist

```
Proactive message?
- [ ] New or requested — not a duplicate
- [ ] Market/session context honest
- [ ] User-approved schedule (if recurring)
- [ ] Clear next action or artifact
- [ ] Can cancel / list jobs
```
