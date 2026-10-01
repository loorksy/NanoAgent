#!/usr/bin/env bash
# Operator entry when §11 is blocked: probe quota, env snapshot, blockers (no LLM beyond probe).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_PROBE=0

usage() {
  echo "Usage: $0 [--skip-probe]" >&2
  echo "  --skip-probe  use cached quota-probe JSONL (no live LLM call)" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-probe) SKIP_PROBE=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ "$SKIP_PROBE" -eq 0 ]]; then
  echo "== live quota probe =="
  if bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
    echo "QUOTA: OK — safe to run rerun_partials / row scripts"
  else
    echo "QUOTA: BLOCKED — add credits or export MOKLI_SECTION11_MODEL before §11 live rows" >&2
    echo "HINT: retry with --skip-probe to inspect env/blockers without another LLM call" >&2
  fi
else
  echo "== cached LLM quota (no live probe) =="
  bash "$ROOT/scripts/vps_section11_quota_status.sh" || true
fi

echo ""
echo "== VPS env =="
bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo ""
echo "== §11 blockers (require-through 13) =="
if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh"; then
  echo ""
  echo "READY: bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13"
  echo "OPERATOR_UNBLOCK_EXIT=0"
  exit 0
fi

echo ""
echo "Runbook: docs/mokli-agent-upgrade-operator-handoff.md (9 steps)"
echo "  bash scripts/mokli_upgrade_section11_rerun_partials.sh"
echo "  bash scripts/mokli_upgrade_section11_remaining_rows.sh"
echo "OPERATOR_UNBLOCK_EXIT=1" >&2
exit 1
