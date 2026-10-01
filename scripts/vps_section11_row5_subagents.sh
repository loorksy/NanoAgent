#!/usr/bin/env bash
# §11 row 5: spawn (wait) + evidence tools. Needs LLM quota (nested subagent call).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-05-subagents-v2.jsonl}"
PROMPT="${2:-Use spawn with wait=true: task \"Summarize XAUUSD in 2 sentences using get_gold_quote or fetch_evidence nodes market_data only.\" Then call fetch_evidence with nodes [\"market_data\"] if not already done. Reply in Arabic. Do not use run_trading_team or analyze_gold.}"

bash "$ROOT/scripts/vps_section11_quota_probe.sh" "quota-before-${OUT}" || {
  echo "Abort row 5: fix LLM quota first (see docs/mokli-agent-upgrade-operator-handoff.md)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
