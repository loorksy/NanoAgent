#!/usr/bin/env bash
# Quick VPS LLM probe for §11 (no patch): one Agent API turn; exit 1 if quota/rate-limit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

OUT="${1:-quota-probe.jsonl}"
HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"

run_probe_checks() {
  local jsonl="$1"
  if grep -q 'Rate limit exceeded\|free-models-per-day' "$jsonl" 2>/dev/null; then
    echo "QUOTA_BLOCKED: OpenRouter free daily limit or 429 in $OUT" >&2
    return 1
  fi
  local extract_cmd
  if [[ "$(id -un)" == "${MOKLI_SERVICE_USER:-nanoagent}" ]]; then
    extract_cmd="cd '$INSTALL_DIR' && source .venv/bin/activate && python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT"
  else
    extract_cmd="sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc \"cd '$INSTALL_DIR' && source .venv/bin/activate && python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT\""
  fi
  local line
  line=$(bash -lc "$extract_cmd" 2>/dev/null || true)
  echo "$line"
  local in_val
  in_val=$(echo "$line" | sed -n 's/.*in=\([0-9]*\).*/\1/p' | head -1)
  if [[ -z "${in_val:-}" || "$in_val" == "0" ]]; then
    echo "QUOTA_BLOCKED: diagnostic input_tokens=0 in $OUT" >&2
    return 1
  fi
  echo "QUOTA_OK in=$in_val file=$OUT"
}

if section11_local_ready "$INSTALL_DIR"; then
  bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" 'Reply with exactly: OK'
  run_probe_checks "$INSTALL_DIR/section11-events/$OUT"
  exit $?
fi

export MOKLI_SSH_HOST="$HOST"
MOKLI_SSH_HOST="$HOST" bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" 'Reply with exactly: OK'

if ssh -o BatchMode=yes "$HOST" \
  "grep -q 'Rate limit exceeded\\|free-models-per-day' ${INSTALL_DIR}/section11-events/$OUT 2>/dev/null"; then
  echo "QUOTA_BLOCKED: OpenRouter free daily limit or 429 in $OUT" >&2
  exit 1
fi

IN=$(ssh -o BatchMode=yes "$HOST" \
  "sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc 'cd ${INSTALL_DIR} && source .venv/bin/activate && \
    python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT'" \
  | sed -n 's/.*in=\([0-9]*\).*/\1/p' | head -1)

if [[ -z "${IN:-}" || "$IN" == "0" ]]; then
  echo "QUOTA_BLOCKED: diagnostic input_tokens=0 in $OUT" >&2
  exit 1
fi

echo "QUOTA_OK in=$IN file=$OUT"
