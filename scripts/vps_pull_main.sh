#!/usr/bin/env bash
# Fast-forward production checkout on VPS (no nginx/certbot). Uses vps_ssh.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
SERVICE_UNIT="${MOKLI_GATEWAY_SERVICE:-nanoagent-gateway}"
BRANCH="${MOKLI_BRANCH:-main}"

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  echo "vps_pull_main: set VPS+VPSPASS or MOKLI_SSH_HOST with working key auth" >&2
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" "$SERVICE_UNIT" "$BRANCH" <<'EOS'
set -euo pipefail
INSTALL="$1"
USER="$2"
UNIT="$3"
BRANCH="$4"
sudo -u "$USER" git -C "$INSTALL" fetch origin "$BRANCH"
sudo -u "$USER" git -C "$INSTALL" checkout -B "$BRANCH" "origin/$BRANCH"
sudo -u "$USER" bash -lc "cd '$INSTALL' && source .venv/bin/activate && pip install -U pip wheel -q && pip install -e '.[trading-mt5]' -q"
sudo systemctl restart "$UNIT"
for _ in $(seq 1 15); do
  if curl -sf http://127.0.0.1:18791/health >/dev/null 2>&1; then
    echo "PULL_OK rev=$(sudo -u "$USER" git -C "$INSTALL" rev-parse --short HEAD)"
    exit 0
  fi
  sleep 2
done
echo "PULL_WARN gateway health not ready after restart" >&2
sudo -u "$USER" git -C "$INSTALL" rev-parse --short HEAD
EOS
