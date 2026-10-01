#!/usr/bin/env bash
# Append check_wake summary to monitor log (no LLM). For Cloud Agent quota-wait turns.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${MOKLI_SECTION11_MONITOR_LOG:-/opt/cursor/artifacts/section11_monitor.log}"
mkdir -p "$(dirname "$LOG")"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  bash "$ROOT/scripts/mokli_upgrade_section11_check_wake.sh" 2>&1 \
    | grep -E 'wake_after_buffer_utc|WAKE_TMUX|closure_errors|seconds_until_reset=' \
    | head -6
  echo "---"
} >>"$LOG"

echo "OK appended monitor snapshot → $LOG"
tail -8 "$LOG"
