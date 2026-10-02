#!/usr/bin/env bash
# Append check_wake summary to monitor log (no LLM). For Cloud Agent quota-wait turns.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${MOKLI_SECTION11_MONITOR_LOG:-/opt/cursor/artifacts/section11_monitor.log}"
WAKE_LOG="${MOKLI_SECTION11_WAKE_LOG:-/opt/cursor/artifacts/timer_wake_wait_quota.log}"
mkdir -p "$(dirname "$LOG")"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  bash "$ROOT/scripts/mokli_upgrade_section11_check_wake.sh" --sync-vps-rev 2>&1 \
    | grep -E 'cloud_agent_rev=|vps_rev=|HINT: VPS rev|wake_after_buffer_utc|WAKE_TMUX|blockers_summary:' \
    | head -10
  if [[ -f "$WAKE_LOG" ]]; then
    grep -E '^(Started timer_wake|Sleeping |WAIT_HEARTBEAT )' "$WAKE_LOG" 2>/dev/null | tail -2
  fi
  echo "---"
} >>"$LOG"

echo "OK appended monitor snapshot → $LOG"
tail -8 "$LOG"
