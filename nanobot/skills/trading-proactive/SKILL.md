---
name: trading-proactive
description: Intelligent proactive gold-trading communication — when to speak, when to stay silent, market-hours honesty, and bespoke user-requested watches via cron or HEARTBEAT. Use for Telegram/WhatsApp notifications, scheduled briefings, holiday/closed-market replies, outcome alerts, or any operator request (including unusual or unforeseen ones) about when and how to be notified.
---

# Trading Proactive Communication

## Core rule

**You decide when to notify — not fixed background bots.**

Do not spam the operator with repetitive scanner notes, "still active" reminders, or compressed-range boilerplate. Proactive messages must pass a **notification gate** (below). Silence is correct when there is nothing new, actionable, or explicitly requested.

Background gold cron jobs (`gold_scan`, `gold_news`, `gold_rec_followup`) are **off by default**. Only enable them when the operator explicitly asks for automatic periodic monitoring and accepts the schedule.

## Not a fixed playbook — the operator is unpredictable

This skill defines **principles and gates**, not a closed list of allowed requests.

The operator's mind holds preferences, habits, and asks you cannot enumerate in advance. They may request things that never appeared in docs or examples — composite conditions, personal rituals, family-time quiet hours, one-off geopolitical fears, custom level watches, or hybrid alerts that mix news + price + open-plan state.

**Your job:**

1. **Listen for intent** in natural language (Arabic or English), including implied needs.
2. **Use memory** — `USER.md`, `memory/MEMORY.md`, session history, past cron jobs, and prior confirmations — to personalize timing, tone, and channel.
3. **Design a bespoke watch** — translate the ask into `cron`, `HEARTBEAT.md`, or a one-shot reply; write the task message so *future you* knows exactly what to evaluate and when to break silence.
4. **Ask only when blocking** — one short clarifying question if time, timezone, or trigger is ambiguous; otherwise propose a sensible default and let them correct you.
5. **Learn** — when they accept, reject, or edit your proposal, remember the preference for next time.

Examples in this file are **illustrations only**. If the operator's request does not match any row in a table, still fulfill it when it is clear and honest.

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
3. If they accept → create a **one-time or recurring cron** (or HEARTBEAT task) with exact time and timezone; confirm in the **operator's language** using their name when known.

**Example tone (render in operator language, not English if they write Arabic):**

> Market is closed today — no live recommendation. Want me to notify you at session open with a short news brief?

If yes:

> Done, {name}. You will get a notification when the session opens at {time} ({tz}).

Use `get_gold_quote` / session context to sanity-check; do not invent open hours.

## User-requested watches (open-ended)

When the operator wants *anything* monitored, reminded, or delivered later — **you** invent the implementation:

| Pattern (not exhaustive) | Typical tool | Notes |
|--------------------------|--------------|-------|
| One-shot at a time | `cron` `at=` | Market open, meeting before NY, pre-FOMC |
| Recurring evaluation | `cron` `every_seconds` / `cron_expr` | Task body = what to check + when to notify |
| Silent until something changes | `HEARTBEAT.md` | Remove task when done |
| Conditional / fuzzy trigger | cron or HEARTBEAT | Describe the condition in the task message for the executing turn |

**Sample intents (not limits — paraphrase in operator language):**

- Sudden high-impact news → alert me to stand aside from trading
- Remind me when my open plan hits TP1
- Quiet after dinner unless price breaks a named level
- Daily pre-London summary with no new recommendation
- Anything else they imagine — map it to a task + notification gate.

Always **confirm** what was scheduled, when it fires, and how to cancel (`cron action="list"` / remove job / delete HEARTBEAT line). Store durable preferences in memory when they ask for ongoing behavior ("from now on", "always", etc.).

## Skill language

Builtin skill files are **English only** (no Arabic or other scripts in `SKILL.md`). Operator-facing chat replies still match the operator's language.

## What not to do

- Do **not** register or assume default `gold_scan` / `gold_rec_followup` jobs unless the user opted in.
- Do **not** send English boilerplate like `Gold scanner: Bot note: compressed range` without user context.
- Do **not** repeat `Open gold SELL still active` on a timer — status updates only on **real transitions** (entered trade, TP1, invalidated) or when the user asks.
- Do **not** add standing HEARTBEAT tasks that re-summarize the same live recommendation every cycle.

## Alerts map

Numeric disconnect/stale seconds are DETERMINISTIC (stale-quote guard). When to speak still uses the notification gate above. Alert map: `gold-trading/references/section-6-alerts.md`.

| Capability | What |
| --- | --- |
| Instant chart with levels | One chart artifact with levels — not spam |
| Human confirm | Human confirm before any MT5 send (HITL; not a Risk Parameters toggle) |
| London/NY morning brief | Optional London/NY morning brief if the operator opted in |
| Daily/weekly scorecard | Daily/weekly scorecard from stores, never invented |
| Natural-language gold questions | Natural-language gold questions answered from tools |
| Stale feed alert | Tell the operator when the feed is dead; do not hallucinate ticks |
| Multi-channel fan-out | Fan-out the same update to configured channels |

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

## Cross-channel delivery (WebUI → Telegram / WhatsApp)

When the operator chats on **WebUI** but asks you to notify them on **Telegram** or **WhatsApp**:

1. Call the **`message`** tool with `channel="telegram"` (or `whatsapp`).
2. **Never** pass the WebUI/WebSocket session UUID as `chat_id` — Telegram requires a **numeric** chat id.
3. If you do not know the numeric id, omit `chat_id` and let the server resolve the approved Telegram operator from pairing — or use **`list_sessions`** / **`send_session_message`** to reach their Telegram session by `@handle`.
4. **Only claim delivery after the tool succeeds.** If the tool returns an error, tell the operator honestly and do not say the message was sent.

## Quick checklist

```
Proactive message?
- [ ] New or requested — not a duplicate
- [ ] Market/session context honest
- [ ] User-approved schedule (if recurring)
- [ ] Clear next action or artifact
- [ ] Can cancel / list jobs
```
