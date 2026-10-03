#!/usr/bin/env bash
# §11 rows 12–13 pre-checks without LLM (Cloud Agent or operator smoke).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== row 12 local (dev UI proxy) =="
bash "$ROOT/scripts/local_section11_row12_smoke.sh"

echo ""
echo "== row 12 VPS (production UI on :8080) =="
bash "$ROOT/scripts/vps_section11_row12_desktop.sh"

echo ""
echo "== row 13 CI proxy (not production 13-mobile.jsonl) =="
bash "$ROOT/scripts/vps_section11_row13_mobile.sh"

echo ""
echo "Close (after live 12-desktop-ui.jsonl + 13-mobile.jsonl):"
echo "  bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json"
echo ""
echo "OK §11 UI prechecks — live JSONL still required: 12-desktop-ui.jsonl, 13-mobile.jsonl"
