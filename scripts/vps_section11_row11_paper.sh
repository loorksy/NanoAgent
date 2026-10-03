#!/usr/bin/env bash
# §11 row 11: propose → save → paper via Agent API (needs OANDA candles + LLM quota).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-11-paper.jsonl}"
PROMPT="${2:-You must use propose_strategy only. Steps: (1) action propose with strategy_name gold_hour_break, leave candles_json empty so the tool loads candles, description: hourly break with 5-candle stop. (2) If proposed and backtest ok, action save with the proposal. (3) action paper with the saved strategy_id. Do not activate live. Summarize run_state and paper ledger result.}"

bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda || {
  echo "Abort row 11: need LLM quota and OANDA_* on VPS (set_oanda_env.sh)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
