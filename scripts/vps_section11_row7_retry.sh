#!/usr/bin/env bash
# §11 row 7: single turn; capture retry events in JSONL (rate_limit / 429 recovery).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-07-retry-v2.jsonl}"
PROMPT="${2:-Reply with exactly: OK}"

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 7: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
