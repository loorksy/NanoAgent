#!/usr/bin/env bash
# §11 row 3: prompt for two distinct tools (gold quote + list_dir). Needs LLM quota.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-03-multi-tool-v2.jsonl}"
PROMPT="${2:-You must call exactly two tools before answering: (1) get_gold_quote for XAUUSD, (2) list_dir with path \".\" on the workspace. Then summarize both results in Arabic. Do not call analyze_gold, run_trading_team, or spawn.}"

bash "$ROOT/scripts/vps_section11_quota_probe.sh" "quota-before-${OUT}" || {
  echo "Abort row 3: fix LLM quota first (see docs/mokli-agent-upgrade-operator-handoff.md)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
