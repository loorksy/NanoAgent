#!/usr/bin/env bash
# §11 row 9: quota probe then multi-round session (folding / in_last_over_first).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-09-long-session-v3.jsonl}"
ROUNDS="${2:-15}"
PROMPT="${3:-Each message: call list_dir with path \".\" exactly once, then reply OK only. Do not call get_gold_quote or analyze_gold.}"

bash "$ROOT/scripts/vps_section11_quota_gate.sh" "quota-before-${OUT}" || {
  echo "Abort row 9: fix LLM quota first (see docs/mokli-agent-upgrade-operator-handoff.md)" >&2
  exit 1
}

exec bash "$ROOT/scripts/vps_section11_long_session.sh" "$OUT" "$ROUNDS" "$PROMPT"
