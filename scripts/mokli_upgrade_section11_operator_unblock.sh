#!/usr/bin/env bash
# Operator entry when §11 is blocked: probe quota, env snapshot, blockers (no LLM beyond probe).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_PROBE=0
DO_PULL=0
BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"

usage() {
  echo "Usage: $0 [--skip-probe] [--pull-vps]" >&2
  echo "  --skip-probe  use cached quota-probe JSONL (no live LLM call)" >&2
  echo "  --pull-vps    vps_pull_main.sh on \$MOKLI_SECTION11_VPS_BRANCH before probe/env" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-probe) SKIP_PROBE=1; shift ;;
    --pull-vps) DO_PULL=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ "$DO_PULL" -eq 1 ]]; then
  echo "== VPS pull ($BRANCH) =="
  bash "$ROOT/scripts/vps_pull_main.sh" "$BRANCH"
fi

if [[ "$SKIP_PROBE" -eq 0 ]]; then
  echo "== live quota probe =="
  if bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
    echo "QUOTA: OK — safe to run rerun_partials / row scripts"
  else
    echo "QUOTA: BLOCKED — add credits or export MOKLI_SECTION11_MODEL before §11 live rows" >&2
    bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true
    echo "HINT: after reset — bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota" >&2
    echo "HINT: or — bash scripts/mokli_upgrade_section11_post_quota.sh --wait --pull-vps" >&2
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
CLOSURE_ERRORS=""
set +e
BLOCK_COMBINED=$(bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" 2>&1)
BLOCK_EC=$?
set -e
printf '%s\n' "$BLOCK_COMBINED"
if [[ "$BLOCK_EC" -eq 0 ]]; then
  echo ""
  echo "READY: bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13"
  echo "OPERATOR_UNBLOCK_EXIT=0"
  exit 0
fi
CLOSURE_ERRORS=$(printf '%s\n' "$BLOCK_COMBINED" | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1)

PARTIAL10_OK=0
PARTIAL10_GATE=0
echo ""
echo "== §11 partial pack (require-through 10; --skip-vps) =="
if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" \
  --skip-vps --require-through 10; then
  PARTIAL10_OK=1
  echo ""
  echo "== production gate @10 (skip quota/OANDA/pull) =="
  if bash "$ROOT/scripts/mokli_upgrade_section11_production_gate.sh" \
    --skip-quota --skip-oanda --skip-pull --require-through 10; then
    PARTIAL10_GATE=1
  fi
fi
echo "operator_unblock: partial10_ok=$PARTIAL10_OK partial10_gate=$PARTIAL10_GATE closure_errors=${CLOSURE_ERRORS:-unknown}"

echo ""
echo "Runbook: docs/mokli-agent-upgrade-operator-handoff.md (9 steps)"
echo "  bash scripts/mokli_upgrade_section11_timer_wake.sh --wait-quota  # full chain when quota OK"
echo "  bash scripts/mokli_upgrade_section11_rerun_partials.sh"
echo "  bash scripts/mokli_upgrade_section11_remaining_rows.sh"
echo "  OANDA: OANDA_API_TOKEN=… OANDA_ACCOUNT_ID=… bash scripts/vps_section11_set_oanda_env.sh"
echo "OPERATOR_UNBLOCK_EXIT=1" >&2
exit 1
