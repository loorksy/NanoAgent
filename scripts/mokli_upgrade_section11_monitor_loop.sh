#!/usr/bin/env bash
# Append check_wake snapshots every N seconds (no LLM). Use in tmux section11-monitor-loop.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL="${MOKLI_SECTION11_MONITOR_INTERVAL_SEC:-1800}"

while true; do
  bash "$ROOT/scripts/mokli_upgrade_section11_monitor_log.sh"
  sleep "$INTERVAL"
done
