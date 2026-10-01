#!/usr/bin/env bash
# §11 row 9: many tool rounds in one Agent API session; append SSE to one JSONL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"
# shellcheck source=scripts/section11_long_session_core.sh
source "$ROOT/scripts/section11_long_session_core.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT_NAME="${1:-09-long-session.jsonl}"
ROUNDS="${2:-15}"
PROMPT="${3:-Call get_gold_quote once only. Reply with OK.}"

if section11_local_ready "$INSTALL_DIR"; then
  section11_run_long_session "$INSTALL_DIR" "$OUT_NAME" "$ROUNDS" "$PROMPT"
  exit 0
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

PROMPT_B64=$(printf '%s' "$PROMPT" | base64 -w0)

vps_ssh env MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" bash -s -- "$INSTALL_DIR" "$OUT_NAME" "$ROUNDS" "$PROMPT_B64" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
ROUNDS="$3"
PROMPT=$(printf '%s' "$4" | base64 -d)
source "$INSTALL/scripts/section11_agent_api_turn_core.sh"
source "$INSTALL/scripts/section11_long_session_core.sh"
section11_run_long_session "$INSTALL" "$OUT_NAME" "$ROUNDS" "$PROMPT"
EOS
