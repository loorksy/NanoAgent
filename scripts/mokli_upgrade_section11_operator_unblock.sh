#!/usr/bin/env bash
# Operator entry when §11 is blocked: probe quota, env snapshot, blockers (no LLM turns beyond probe).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== live quota probe =="
if bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
  echo "QUOTA: OK — safe to run rerun_partials / row scripts"
else
  echo "QUOTA: BLOCKED — add credits or export MOKLI_SECTION11_MODEL before §11 live rows" >&2
fi

echo ""
echo "== VPS env =="
bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo ""
echo "== §11 blockers (require-through 13) =="
if bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh"; then
  echo ""
  echo "READY: bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13"
  exit 0
fi

echo ""
echo "Runbook: docs/mokli-agent-upgrade-operator-handoff.md (9 steps)"
echo "  bash scripts/mokli_upgrade_section11_rerun_partials.sh"
echo "  bash scripts/mokli_upgrade_section11_remaining_rows.sh"
exit 1
