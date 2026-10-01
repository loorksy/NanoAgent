#!/usr/bin/env bash
# §11 row 4: full gold analysis / kernel + structured decision card.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-04-gold-analysis-v2.jsonl}"
PROMPT="${2:-Analyze gold (XAUUSD) for a buy/wait decision. Use run_trading_kernel. Reply in Arabic; expect a structured decision card with res_* id when analysis completes.}"

bash "$ROOT/scripts/vps_section11_quota_probe.sh" "quota-before-${OUT}" || {
  echo "Abort row 4: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
