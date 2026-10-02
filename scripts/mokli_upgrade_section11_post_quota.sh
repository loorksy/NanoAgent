#!/usr/bin/env bash
# After OpenRouter quota returns: optional VPS pull, wait+probe or probe, partial reruns, sync.
# Rows 11–13 (UI pipe / device JSONL) still require mokli_upgrade_section11_remaining_rows.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
SECTION11_EVENTS="$ROOT/section11-events"
SECTION11_RESULTS="$ROOT/section11-results-partial.json"
DO_WAIT=0
DO_PULL=0
SKIP_RERUN=0

usage() {
  echo "Usage: $0 [--wait] [--pull-vps] [--skip-rerun]" >&2
  echo "  --wait       sleep until X-RateLimit-Reset+buffer, then live probe" >&2
  echo "  --pull-vps   sync Cloud branch + check_wake --sync-vps-rev before probe" >&2
  echo "  --skip-rerun skip mokli_upgrade_section11_rerun_partials.sh (probe only)" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait) DO_WAIT=1; shift ;;
    --pull-vps) DO_PULL=1; shift ;;
    --skip-rerun) SKIP_RERUN=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ "$DO_PULL" -eq 1 ]]; then
  bash "$ROOT/scripts/mokli_upgrade_section11_sync_cloud_branch.sh" || true
  echo "== VPS git (pull if behind Cloud) =="
  bash "$ROOT/scripts/mokli_upgrade_section11_check_wake.sh" --sync-vps-rev || true
fi

echo "== LLM quota =="
if [[ "$DO_WAIT" -eq 1 ]]; then
  bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" --wait
else
  bash "$ROOT/scripts/vps_section11_quota_probe.sh"
fi

if [[ "$SKIP_RERUN" -eq 0 ]]; then
  echo "== partial reruns + sync =="
  bash "$ROOT/scripts/mokli_upgrade_section11_rerun_partials.sh"
  if bash "$ROOT/scripts/mokli_upgrade_section11_try_row11_paper.sh"; then
    :
  else
    echo "WARN: row 11 paper failed — rerun bash scripts/vps_section11_row11_paper.sh" >&2
  fi
  if bash "$ROOT/scripts/mokli_upgrade_section11_try_row12_pipe.sh"; then
    :
  else
    echo "WARN: row 12 pipe failed — rerun bash scripts/vps_section11_row12_pipe_turn.sh" >&2
  fi
  echo ""
  echo "== §11 blockers snapshot (--skip-vps @13) =="
  bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" --skip-vps --require-through 13 \
    "$SECTION11_EVENTS" "$SECTION11_RESULTS" 2>&1 || true
fi

cat <<NOTE

Quota OK and partial reruns finished (if not --skip-rerun).
Next (full chain): bash scripts/mokli_upgrade_section11_timer_wake.sh  # add --wait-quota if probe was blocked earlier
  bash scripts/mokli_upgrade_section11_remaining_rows.sh   # rows 11–13 runbook (text only; run row scripts + UI/device)
  bash scripts/mokli_upgrade_section11_operator_unblock.sh # must exit 0
  bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json

NOTE
