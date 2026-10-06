#!/usr/bin/env bash
# Re-run §11 rows that are commonly PARTIAL after quota/OANDA are fixed (operator).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

section11_after_p0_in_ok() {
  local ap="$ROOT/section11-events/01-no-tools-after-p0.jsonl"
  [[ -f "$ap" ]] || return 1
  local line in_val
  line=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_diagnostic_extract.py" --file "$ap" 2>/dev/null || true)
  in_val=$(section11_parse_probe_in "$line")
  [[ -n "$in_val" && "$in_val" -gt 0 ]]
}

if [[ -d "$ROOT/section11-events" ]]; then
  section11_prune_row5_stale_no_nested "$ROOT/section11-events" "$ROOT"
fi

echo "== VPS readiness (quota; OANDA warned for row 10/11) =="
bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota || exit 1
bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo "== P0 row 1 after =="
if section11_after_p0_in_ok; then
  echo "SKIP P0 row 1 after — 01-no-tools-after-p0.jsonl already has in>0"
else
  bash "$ROOT/scripts/vps_section11_row1_after_p0.sh"
fi

RERUN_ROWS=$("$PYTHON" "$ROOT/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$ROOT/section11-events" --require-through 13 --print-live-rerun-rows 2>/dev/null || true)
echo "== partial rows (live quality gaps: ${RERUN_ROWS:-none}) =="
for row_id in $RERUN_ROWS; do
  case "$row_id" in
    3) bash "$ROOT/scripts/vps_section11_row3_multi_tool.sh" ;;
    5) bash "$ROOT/scripts/vps_section11_row5_subagents.sh" ;;
    8) bash "$ROOT/scripts/vps_section11_row8_fallback_provider.sh" ;;
    9) bash "$ROOT/scripts/vps_section11_row9_long_session.sh" ;;
    10)
      if bash "$ROOT/scripts/vps_section11_env_check.sh" --require-oanda 2>/dev/null; then
        bash "$ROOT/scripts/vps_section11_row10_backtest.sh"
      else
        echo "SKIP row 10: OANDA not configured" >&2
      fi
      ;;
    *) echo "WARN: no rerun script mapped for row $row_id" >&2 ;;
  esac
done
if [[ -z "${RERUN_ROWS// /}" ]]; then
  echo "SKIP partial row scripts — JSONL quality OK for rows 3,5,8,9,10"
fi

echo "== sync JSONL from VPS + P0 table =="
bash "$ROOT/scripts/mokli_upgrade_section11_sync_from_vps.sh" --pull-vps \
  "$ROOT/section11-events" "$ROOT/section11-results-partial.json" 13

cat <<'NOTE'
Next: rows 11–13 — bash scripts/mokli_upgrade_section11_remaining_rows.sh
Close: bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json
NOTE
