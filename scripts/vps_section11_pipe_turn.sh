#!/usr/bin/env bash
# Run one Mokli pipe turn on VPS and write gateway JSONL (§11 row 12 helper).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"
# shellcheck source=scripts/section11_pipe_turn_core.sh
source "$ROOT/scripts/section11_pipe_turn_core.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT_NAME="${1:-12-desktop-ui.jsonl}"
PROMPT="${2:-حلل الذهب (XAUUSD) لقرار شراء أو انتظار. استخدم run_trading_kernel. رد بالعربية مع بطاقة قرار منظمة.}"

if section11_local_ready "$INSTALL_DIR"; then
  section11_run_pipe_turn "$INSTALL_DIR" "$OUT_NAME" "$PROMPT"
  exit 0
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

PROMPT_B64=$(printf '%s' "$PROMPT" | base64 -w0)

vps_ssh env MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" bash -s -- "$INSTALL_DIR" "$OUT_NAME" "$PROMPT_B64" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
PROMPT=$(printf '%s' "$3" | base64 -d)
# shellcheck source=scripts/section11_pipe_turn_core.sh
source "$INSTALL/scripts/section11_pipe_turn_core.sh"
section11_run_pipe_turn "$INSTALL" "$OUT_NAME" "$PROMPT"
EOS
