#!/usr/bin/env bash
# Copy operator §11 JSONL from VPS install dir to local ./section11-events/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
LOCAL_DIR="${1:-$ROOT/section11-events}"

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

mkdir -p "$LOCAL_DIR"
scp -o BatchMode=yes -r "${HOST}:${INSTALL_DIR}/section11-events/*.jsonl" "$LOCAL_DIR/" 2>/dev/null || {
  echo "WARN: no JSONL on VPS under ${INSTALL_DIR}/section11-events/" >&2
  exit 1
}
echo "OK pulled JSONL → $LOCAL_DIR"
ls -1 "$LOCAL_DIR"/*.jsonl 2>/dev/null | wc -l | xargs -I{} echo "files={}"
