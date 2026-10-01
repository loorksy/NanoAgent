#!/usr/bin/env bash
# Same closure sequence as Cloud Agent timer mokli-section11-after-openrouter-reset.
# Stops early if quota still blocked; does not bypass OANDA or missing row 11–13 JSONL.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/pytest"
[[ -x "$PY" ]] || PY=pytest

echo "== §11 completion status (cached) =="
bash "$ROOT/scripts/mokli_upgrade_section11_completion_status.sh" || true

set -e

echo ""
echo "== after OpenRouter reset (live probe + partial reruns) =="
if ! bash "$ROOT/scripts/mokli_upgrade_section11_after_reset_wake.sh"; then
  echo "TIMER_WAKE_EXIT=1 (after_reset_wake failed — quota/OANDA/LLM)" >&2
  exit 1
fi

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_remaining_rows.sh"

echo ""
echo "== sync + production unblock =="
bash "$ROOT/scripts/mokli_upgrade_section11_sync_from_vps.sh" --pull-vps

if ! bash "$ROOT/scripts/mokli_upgrade_section11_operator_unblock.sh" --pull-vps; then
  echo "TIMER_WAKE_EXIT=1 (operator_unblock — finish rows 11–13 JSONL + OANDA)" >&2
  exit 1
fi

echo ""
echo "== close report @13 =="
bash "$ROOT/scripts/mokli_upgrade_section11_close.sh" --apply --require-through 13
"$PY" tests/scripts/test_mokli_upgrade_report_section11_gate.py -q

echo "TIMER_WAKE_EXIT=0"
echo "Verify docs/mokli-agent-upgrade-report.md §11 rows 1–13 before marking upgrade complete."
