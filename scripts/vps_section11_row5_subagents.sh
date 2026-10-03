#!/usr/bin/env bash
# §11 row 5: spawn (wait) + evidence tools. Needs LLM quota (nested subagent call).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
OUT="${1:-05-subagents-v2.jsonl}"
PROMPT="${2:-Before spawn, call fetch_evidence with nodes [\"market_data\"] once. Then spawn with wait=true: task \"Write one Arabic sentence summarizing only the market_data evidence JSON from the parent turn; do not call tools.\" Reply in Arabic with both the evidence summary and the spawn result. Do not use run_trading_team, analyze_gold, or get_gold_quote.}"

EVENT_DIR="${MOKLI_SECTION11_EVENTS:-$ROOT/section11-events}"
section11_prune_row5_stale_no_nested "$EVENT_DIR" "$ROOT"
section11_prune_quota_failed_output "$EVENT_DIR" "$OUT" "$ROOT"

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 5: fix LLM quota first (see docs/mokli-agent-upgrade-operator-handoff.md)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
