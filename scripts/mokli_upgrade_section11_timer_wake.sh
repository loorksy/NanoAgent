#!/usr/bin/env bash
# Same closure sequence as Cloud Agent timer mokli-section11-after-openrouter-reset.
# Stops early if quota still blocked; does not bypass OANDA or missing row 11–13 JSONL.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SECTION11_EVENTS="$ROOT/section11-events"
SECTION11_RESULTS="$ROOT/section11-results-partial.json"
SECTION11_REQUIRE=13
DRY_RUN=0
WAIT_QUOTA=0

usage() {
  echo "Usage: $0 [--dry-run] [--wait-quota]" >&2
  echo "  --dry-run     completion_status only; no live probe or close" >&2
  echo "  --wait-quota  if probe blocked, sleep until X-RateLimit-Reset+buffer then continue" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --wait-quota) WAIT_QUOTA=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

echo "== §11 completion status (cached) =="
bash "$ROOT/scripts/mokli_upgrade_section11_completion_status.sh" || true

if [[ "$DRY_RUN" -eq 1 ]]; then
  wait_note=""
  [[ "$WAIT_QUOTA" -eq 1 ]] && wait_note=" (with --wait-quota: sleep until reset+buffer if probe blocked, then same chain)"
  cat <<NOTE
DRY-RUN: would next run${wait_note}: after_reset_wake (probe, rerun_partials, try_row11) → remaining_rows (runbook) → try_row11 → sync --pull-vps → operator_unblock --pull-vps → close --apply @13 (report gate inside close)
NOTE
  echo "TIMER_WAKE_EXIT=0 (dry-run)"
  exit 0
fi

set -e

LOCK_FILE="${MOKLI_SECTION11_TIMER_WAKE_LOCK:-/tmp/mokli_section11_timer_wake.lock}"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "TIMER_WAKE_EXIT=2 (another timer_wake holds $LOCK_FILE)" >&2
  exit 2
fi
echo "TIMER_WAKE_LOCK=$LOCK_FILE"
trap 'echo "TIMER_WAKE_FINAL_EXIT=$?"' EXIT

bash "$ROOT/scripts/mokli_upgrade_section11_sync_cloud_branch.sh" || true

if [[ "$WAIT_QUOTA" -eq 1 ]]; then
  echo ""
  echo "== optional wait for OpenRouter reset =="
  if ! bash "$ROOT/scripts/vps_section11_quota_probe.sh"; then
    bash "$ROOT/scripts/mokli_upgrade_section11_wait_quota_reset.sh" --wait 2>&1
  fi
fi

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_sync_cloud_branch.sh" || true
echo ""
echo "== VPS git (match Cloud tip before live §11) =="
bash "$ROOT/scripts/mokli_upgrade_section11_check_wake.sh" --sync-vps-rev || true
echo ""
echo "== after OpenRouter reset (live probe + partial reruns) =="
if ! bash "$ROOT/scripts/mokli_upgrade_section11_after_reset_wake.sh"; then
  echo "TIMER_WAKE_EXIT=1 (after_reset_wake failed — quota/OANDA/LLM)" >&2
  exit 1
fi

echo ""
bash "$ROOT/scripts/mokli_upgrade_section11_remaining_rows.sh"
echo ""
echo "NOTE: remaining_rows.sh prints the row 11–13 runbook only (no LLM/UI)." >&2
echo "NOTE: row 12 needs Mokli UI pipe JSONL; row 13 needs device/SDK JSONL — see operator-handoff." >&2

if bash "$ROOT/scripts/mokli_upgrade_section11_try_row11_paper.sh"; then
  :
else
  echo "WARN: row 11 paper failed — rerun bash scripts/vps_section11_row11_paper.sh" >&2
fi

echo ""
echo "== sync + production unblock =="
bash "$ROOT/scripts/mokli_upgrade_section11_sync_from_vps.sh" --pull-vps \
  "$SECTION11_EVENTS" "$SECTION11_RESULTS" "$SECTION11_REQUIRE"

if ! bash "$ROOT/scripts/mokli_upgrade_section11_operator_unblock.sh" --pull-vps; then
  echo "TIMER_WAKE_EXIT=1 (operator_unblock — finish rows 11–13 JSONL + OANDA)" >&2
  exit 1
fi

echo ""
echo "== close report @13 (includes §11 report gate pytest on canonical report) =="
if ! bash "$ROOT/scripts/mokli_upgrade_section11_close.sh" --apply --require-through 13 \
  --dir "$SECTION11_EVENTS" --results "$SECTION11_RESULTS"; then
  echo "TIMER_WAKE_EXIT=1 (close @13 failed — partial reruns may still help; see blockers_summary)" >&2
  bash "$ROOT/scripts/mokli_upgrade_section11_blockers.sh" --skip-vps --require-through 13 \
    "$SECTION11_EVENTS" "$SECTION11_RESULTS" 2>&1 || true
  echo "HINT: rows 11–13 — bash scripts/mokli_upgrade_section11_remaining_rows.sh" >&2
  exit 1
fi

echo "TIMER_WAKE_EXIT=0"
echo "Verify docs/mokli-agent-upgrade-report.md §11 rows 1–13 before marking upgrade complete."
