#!/usr/bin/env bash
# Ensure §11 JSONL under section11-events/ is writable by the gateway user (fix root-owned files from SSH probes).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
export MOKLI_SSH_HOST="$HOST"

_fix_local() {
  local install="$1"
  local user="$2"
  if [[ ! -d "$install/section11-events" ]]; then
    echo "SKIP no $install/section11-events"
    return 0
  fi
  chown -R "$user:$user" "$install/section11-events"
  echo "OK chown $install/section11-events -> $user"
}

if [[ -d "$INSTALL_DIR/section11-events" ]] \
  && [[ -f "$INSTALL_DIR/.mokli/workspace/agent_api/admin_token" ]]; then
  _fix_local "$INSTALL_DIR" "$SERVICE_USER"
  exit 0
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" <<'EOS'
set -euo pipefail
install="$1"
user="$2"
if [[ ! -d "$install/section11-events" ]]; then
  echo "SKIP no section11-events on VPS"
  exit 0
fi
chown -R "$user:$user" "$install/section11-events"
echo "OK chown $install/section11-events -> $user"
EOS
