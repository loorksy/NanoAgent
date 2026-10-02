#!/usr/bin/env bash
# §11 row 8: fallback chain — operator must align modelPreset on VPS before this turn.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-08-fallback-provider-v2.jsonl}"
PROMPT="${2:-Reply with exactly: OK}"

cat <<'NOTE' >&2
§11 row 8: set modelPreset=null (OpenRouter) or disable primary billing provider in
~/.mokli/config.json on VPS, then confirm retry events show state=cleared on fallback.
See docs/mokli-agent-upgrade-operator-handoff.md (OpenRouter / Anthropic preset).
NOTE

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 8: fix LLM quota first" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
