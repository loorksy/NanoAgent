#!/usr/bin/env bash
# §11 row 2: single-tool gold quote turn (explicit prompt).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-02-single-tool-v3.jsonl}"
PROMPT="${2:-What is the current XAUUSD gold price? Use get_gold_quote only, then answer in one short Arabic sentence.}"

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 2: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
