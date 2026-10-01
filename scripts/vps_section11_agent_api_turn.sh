#!/usr/bin/env bash
# Run one Agent API turn on VPS and write JSONL + diagnostic line (operator §11 helper).
# From workstation: MOKLI_SSH_HOST or VPS/VPSPASS. On the VPS host: auto localhost if Agent API is up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT_NAME="${1:-01-no-tools.jsonl}"
PROMPT="${2:-مرحبا، ما اسمك؟}"

if section11_local_ready "$INSTALL_DIR"; then
  section11_run_agent_api_turn "$INSTALL_DIR" "$OUT_NAME" "$PROMPT"
  exit 0
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

PROMPT_B64=$(printf '%s' "$PROMPT" | base64 -w0)

vps_ssh bash -s -- "$INSTALL_DIR" "$OUT_NAME" "$PROMPT_B64" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
PROMPT=$(printf '%s' "$3" | base64 -d)
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$INSTALL/scripts/section11_agent_api_turn_core.sh"
section11_run_agent_api_turn "$INSTALL" "$OUT_NAME" "$PROMPT"
EOS
