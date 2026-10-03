#!/usr/bin/env bash
# §11 row 12: headless Mokli pipe turn (same gateway path as UI pipe) + gateway JSONL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-12-desktop-ui.jsonl}"
PROMPT="${2:-حلل الذهب (XAUUSD) لقرار شراء أو انتظار. استخدم run_trading_kernel. رد بالعربية مع بطاقة قرار منظمة.}"

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 12 pipe: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_pipe_turn.sh" "$OUT" "$PROMPT"
