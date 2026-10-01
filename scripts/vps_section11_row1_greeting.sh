#!/usr/bin/env bash
# §11 row 1: no-tools greeting turn (baseline before P0 after compare).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-01-no-tools-v2.jsonl}"
PROMPT="${2:-مرحبا، ما اسمك؟}"

bash "$ROOT/scripts/vps_section11_quota_probe.sh" "quota-before-${OUT}" || {
  echo "Abort row 1: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
