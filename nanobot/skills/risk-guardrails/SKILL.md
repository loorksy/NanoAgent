---
name: risk-guardrails
description: Gold risk judgment around live capital gates — lot size, daily drawdown, spread, cooldown, max positions, minimum R:R, and operator-owned WebUI thresholds. Use when sizing, when a plan is blocked, after losses, or when the operator asks to loosen risk. English skill; reply in the operator's language.
---

# Risk guardrails (gold)

DETERMINISTIC numbers are owned by `Config.trading_risk_parameters` and `policy.live()`. This skill teaches how to talk and think around those gates without inventing a second rulebook.

## References

- Spec section 3: [references/section-3-risk.md](references/section-3-risk.md)
- Playbook stops / discipline: `nanobot/skills/xauusd-playbook/references/` (`P-026` … `P-055`, `P-181` … `P-200`)

## Steps

1. Size from stop distance and `live()` risk percent. Dual-check lots (playbook 188). Balance, not floating equity, for lot growth (199).
2. If a gate vetoes, the recommendation is unpublished. Do not flip side to "save" the idea.
3. Operator WebUI edits apply on the next evaluation. Do not lecture that a value is "too dangerous" — type/range checks already ran. One warning string exists in `i18n` (`risk.operator_warning`).
4. Human-in-the-loop propose→confirm is not a risk parameter. Never skip it. Playbook 182 (zero-hesitation auto-send) is excluded.

## Output

- Whether capital gates allow a plan.
- Which user-facing check refused (from `i18n.gate_label`), not G8/G12 ids.
- What the operator can change in Risk Parameters if they own the threshold.

## Example

Operator: "widen the stop so RR becomes 1:1.2."
You: "The reward-to-risk check still needs the farthest target at the configured minimum. Changing the stop without a farther target will keep the plan blocked."

## Do not

- Memorize 1%, 2%, 3%, 60-point spread, or 1:2 as if they were prompt constants — they are live config.
- Widen a stop after entry to "give it room" (playbook 35).
- Stack a second gold add onto an already-losing same-side position (184).
