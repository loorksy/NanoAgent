#!/usr/bin/env bash
# §11 row 6: tool failure row (get_gold_quote fails cleanly when feed unconfigured).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-06-tool-failure-v2.jsonl}"
PROMPT="${2:-What is the live XAUUSD price? You must call get_gold_quote once. If the tool fails, report the failure to the user and do not invent a price. Reply in Arabic.}"

bash "$ROOT/scripts/vps_section11_quota_probe.sh" "quota-before-${OUT}" || {
  echo "Abort row 6: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
