#!/usr/bin/env bash
# Report Cloud Agent background timer_wake --wait-quota (tmux + log). No LLM.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
LOG="${MOKLI_SECTION11_WAKE_LOG:-/opt/cursor/artifacts/timer_wake_wait_quota.log}"
SESSION="${MOKLI_SECTION11_WAKE_TMUX:-section11-timer-wake-wait}"

echo "== OpenRouter reset =="
RESET_OUT=$(bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true)
printf '%s\n' "$RESET_OUT"
section11_emit_wake_after_buffer "$RESET_OUT"

echo ""
echo "== tmux session: $SESSION =="
if tmux -f /exec-daemon/tmux.portal.conf has-session -t "$SESSION" 2>/dev/null; then
  echo "WAKE_TMUX=running"
else
  echo "WAKE_TMUX=missing"
  echo "HINT: bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota" >&2
fi

echo ""
echo "== wake log: $LOG =="
if [[ -f "$LOG" ]]; then
  echo "WAKE_LOG_BYTES=$(wc -c < "$LOG")"
  markers=$(
    grep -E \
      '^(Started timer_wake|Sleeping |WAIT_HEARTBEAT |PULL_OK |QUOTA:|STILL_BLOCKED|after_reset_wake|TIMER_WAKE_EXIT|TIMER_WAKE_FINAL_EXIT|close_summary:)' \
      "$LOG" 2>/dev/null | tail -20
  )
  if [[ -n "$markers" ]]; then
    printf '%s\n' "$markers"
  else
    tail -8 "$LOG"
  fi
else
  echo "WAKE_LOG=missing"
fi

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" --skip-vps --require-through 13 2>&1 \
  | grep -E 'blockers_summary:|closure_errors=' | tail -2 || true
