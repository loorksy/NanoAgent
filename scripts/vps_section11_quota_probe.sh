#!/usr/bin/env bash
# Quick VPS LLM probe for §11 (no patch): one Agent API turn; exit 1 if quota/rate-limit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-quota-probe.jsonl}"

HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
export MOKLI_SSH_HOST="$HOST"

MOKLI_SSH_HOST="$HOST" bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" 'Reply with exactly: OK' \
  | tee >(cat >&2)

if ssh -o BatchMode=yes "$HOST" \
  "grep -q 'Rate limit exceeded\\|free-models-per-day' /opt/nanoagent/section11-events/$OUT 2>/dev/null"; then
  echo "QUOTA_BLOCKED: OpenRouter free daily limit or 429 in $OUT" >&2
  exit 1
fi

IN=$(ssh -o BatchMode=yes "$HOST" \
  "sudo -u nanoagent bash -lc 'cd /opt/nanoagent && source .venv/bin/activate && \
    python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT'" \
  | sed -n 's/.*in=\([0-9]*\).*/\1/p' | head -1)

if [[ -z "${IN:-}" || "$IN" == "0" ]]; then
  echo "QUOTA_BLOCKED: diagnostic input_tokens=0 in $OUT" >&2
  exit 1
fi

echo "QUOTA_OK in=$IN file=$OUT"
