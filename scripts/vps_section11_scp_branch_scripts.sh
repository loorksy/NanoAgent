#!/usr/bin/env bash
# When Cloud Agent git push is blocked, copy critical §11 scripts to VPS (same paths as repo).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"

FILES=(
  scripts/mokli_upgrade_section11_validate.py
  scripts/mokli_upgrade_section11_validate.sh
  scripts/mokli_upgrade_diagnostic_extract.py
  scripts/mokli_upgrade_section11_rerun_partials.sh
  scripts/mokli_upgrade_section11_blockers.sh
  scripts/mokli_upgrade_section11_operator_unblock.sh
  scripts/mokli_upgrade_section11_close.sh
  scripts/mokli_upgrade_section11_after_reset_wake.sh
  scripts/mokli_upgrade_section11_sync_cloud_branch.sh
  scripts/section11_quota_hints.sh
  scripts/section11_agent_api_turn_core.sh
  scripts/section11_pipe_turn_core.py
  scripts/section11_pipe_turn_core.sh
  scripts/vps_section11_pipe_turn.sh
  scripts/vps_section11_row12_pipe_turn.sh
  scripts/mokli_upgrade_section11_try_row12_pipe.sh
  scripts/vps_section11_row5_subagents.sh
  scripts/vps_section11_env_check.sh
)

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for rel in "${FILES[@]}"; do
  cp "$ROOT/$rel" "$TMP/"
done

scp -o BatchMode=yes -o ConnectTimeout=15 "$TMP"/* "${MOKLI_SSH_HOST}:/tmp/mokli-section11-scripts/"
N="${#FILES[@]}"
vps_ssh bash -s -- "$INSTALL" "$SERVICE_USER" "$N" <<'EOS'
set -euo pipefail
INSTALL="$1"
USER="$2"
N="$3"
for f in /tmp/mokli-section11-scripts/*; do
  base=$(basename "$f")
  sudo cp "$f" "$INSTALL/scripts/$base"
  sudo chown "$USER:$USER" "$INSTALL/scripts/$base"
done
echo "OK scp scripts → $INSTALL/scripts ($N files)"
EOS

echo "HINT: git push when token works, then vps_pull_main.sh replaces scp copies" >&2
