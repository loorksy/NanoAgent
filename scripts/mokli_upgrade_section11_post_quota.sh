#!/usr/bin/env bash
# After OpenRouter quota returns: optional VPS pull, wait+probe or probe, partial reruns, sync.
# Rows 11–13 (UI pipe / device JSONL) still require mokli_upgrade_section11_remaining_rows.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
DO_WAIT=0
DO_PULL=0
SKIP_RERUN=0

usage() {
  echo "Usage: $0 [--wait] [--pull-vps] [--skip-rerun]" >&2
  echo "  --wait       sleep until X-RateLimit-Reset+buffer, then live probe" >&2
  echo "  --pull-vps   vps_pull_main.sh on \$MOKLI_SECTION11_VPS_BRANCH before probe" >&2
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
  echo "== VPS pull ($BRANCH) =="
  bash "$ROOT/scripts/vps_pull_main.sh" "$BRANCH"
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
fi

cat <<NOTE

Quota OK and partial reruns finished (if not --skip-rerun).
Next:
  bash scripts/mokli_upgrade_section11_remaining_rows.sh   # rows 11–13 runbook
  bash scripts/mokli_upgrade_section11_operator_unblock.sh # must exit 0
  bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13

NOTE
