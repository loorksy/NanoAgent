#!/usr/bin/env bash
# Cloud Agent / timer wake: resume §11 after OpenRouter daily reset (no long sleep).
# Does not fill rows 11–13 (UI/device) — operator still runs remaining_rows.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"

echo "== VPS pull ($BRANCH) =="
bash "$ROOT/scripts/vps_pull_main.sh" "$BRANCH"

echo "== live quota probe =="
if ! bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
  bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" 2>&1 || true
  echo "STILL_BLOCKED: add OpenRouter credits or export MOKLI_SECTION11_MODEL before §11 live rows" >&2
  echo "HINT: OANDA — bash scripts/vps_section11_set_oanda_env.sh" >&2
  exit 1
fi

echo "== OANDA (rows 10–11) =="
if ! bash "$ROOT/scripts/vps_section11_env_check.sh" --require-oanda; then
  echo "WARN: OANDA not configured — row 10/11 skip until vps_section11_set_oanda_env.sh" >&2
fi

echo "== partial reruns + sync =="
bash "$ROOT/scripts/mokli_upgrade_section11_rerun_partials.sh"

echo ""
echo "== operator unblock check =="
if bash "$ROOT/scripts/mokli_upgrade_section11_operator_unblock.sh" --skip-probe; then
  echo "READY for remaining_rows (11–13) and close --apply @13 when JSONL complete"
else
  echo "PARTIAL: reruns done but blockers remain (OANDA and/or rows 11–13 JSONL)" >&2
  bash "$ROOT/scripts/mokli_upgrade_section11_remaining_rows.sh"
  exit 1
fi
