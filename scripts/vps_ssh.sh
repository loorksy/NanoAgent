#!/usr/bin/env bash
# Run SSH to the Mokli VPS: password (VPS/VPSPASS) or key (~/.ssh/config host).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_env.sh
source "$ROOT/scripts/vps_env.sh"
# shellcheck source=scripts/vps_ssh_target.sh
source "$ROOT/scripts/vps_ssh_target.sh"

MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-}"

vps_ssh_ready() {
  if [[ -n "${MOKLI_SSH_HOST:-}" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=15 "$MOKLI_SSH_HOST" true 2>/dev/null
    return $?
  fi
  if [[ -n "${VPS:-}" && -n "${VPSPASS:-}" ]]; then
    return 0
  fi
  return 1
}

vps_ssh() {
  if [[ -n "${MOKLI_SSH_HOST:-}" ]]; then
    ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 "$MOKLI_SSH_HOST" "$@"
    return
  fi
  local target
  target="$(normalize_vps_ssh_target "${VPS:-}")"
  command -v sshpass >/dev/null || {
    echo "vps_ssh: sshpass required for password auth" >&2
    exit 1
  }
  sshpass -p "$VPSPASS" ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 "$target" "$@"
}
