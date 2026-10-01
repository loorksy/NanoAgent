#!/usr/bin/env bash
# §11 row 10: fast_backtest on OANDA-loaded candles (needs quota + OANDA).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-10-backtest-v2.jsonl}"
PROMPT="${2:-Call fast_backtest only once. Leave candles_json empty so the tool loads candles from the market feed. Summarize ok, trades count, and any reason_key in Arabic. Do not paste candle arrays in your reply.}"

bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda || {
  echo "Abort row 10: need LLM quota and OANDA_* on VPS (set_oanda_env.sh)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" "$PROMPT"
