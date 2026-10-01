#!/usr/bin/env bash
# Re-run §11 rows that are commonly PARTIAL after quota/OANDA are fixed (operator).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== VPS readiness (quota; OANDA warned for row 10/11) =="
bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota || exit 1
bash "$ROOT/scripts/vps_section11_env_check.sh" || true

echo "== P0 row 1 after =="
bash "$ROOT/scripts/vps_section11_row1_after_p0.sh"

echo "== partial rows 3, 5, 9 (writes 03-multi-tool-v2, 05-subagents-v2, 09-long-session-v3 on VPS) =="
bash "$ROOT/scripts/vps_section11_row3_multi_tool.sh"
bash "$ROOT/scripts/vps_section11_row5_subagents.sh"
bash "$ROOT/scripts/vps_section11_row9_long_session.sh"

if bash "$ROOT/scripts/vps_section11_env_check.sh" --require-oanda 2>/dev/null; then
  echo "== row 10 backtest (OANDA ok) =="
  bash "$ROOT/scripts/vps_section11_row10_backtest.sh"
else
  echo "SKIP row 10: OANDA not configured" >&2
fi

echo "== sync JSONL from VPS + P0 table =="
bash "$ROOT/scripts/mokli_upgrade_section11_sync_from_vps.sh"

cat <<'NOTE'
Next: rows 11–13 — bash scripts/mokli_upgrade_section11_remaining_rows.sh
Close: bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13
NOTE
