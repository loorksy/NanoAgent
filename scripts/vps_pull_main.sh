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
# Optional: bash scripts/vps_pull_main.sh cursor/section11-vps-rows-d9e1
if [[ $# -ge 1 && "$1" != -* ]]; then
  BRANCH="$1"
  shift
fi
if [[ $# -gt 0 ]]; then
  echo "Usage: $0 [branch]" >&2
  echo "  branch defaults to MOKLI_BRANCH or main" >&2
  exit 2
fi

echo "vps_pull_main: branch=$BRANCH install=$INSTALL_DIR" >&2
expected="${MOKLI_SECTION11_VPS_BRANCH:-cursor/section11-vps-rows-d9e1}"
if [[ "$BRANCH" == main && "$expected" != main ]]; then
  echo "WARN: default branch is main; §11 closure may need: bash $0 ${expected}" >&2
fi

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
sudo -u "$USER" bash -lc "cd '$INSTALL' && source .venv/bin/activate && pip install -U pip wheel -q && pip install -q -e '.[trading-mt5]' 'python-telegram-bot[socks,webhooks]>=22.6,<23.0' 'socksio>=1.0.0,<2.0.0' 'python-socks[asyncio]>=2.8.0,<3.0.0' 'neonize>=0.4.3.post0,<0.5.0' 'segno>=1.6.1,<2.0.0'"
if [[ -d "$INSTALL/section11-events" ]]; then
  chown -R "$USER:$USER" "$INSTALL/section11-events"
fi
sudo systemctl restart "$UNIT"
REV=$(sudo -u "$USER" git -C "$INSTALL" rev-parse --short HEAD)
GW_OK=0
API_OK=0
for _ in $(seq 1 15); do
  curl -sf http://127.0.0.1:18791/health >/dev/null 2>&1 && GW_OK=1
  curl -sf http://127.0.0.1:8766/api/v2/health >/dev/null 2>&1 && API_OK=1
  if [[ "$GW_OK" -eq 1 && "$API_OK" -eq 1 ]]; then
    echo "PULL_OK rev=$REV"
    exit 0
  fi
  sleep 2
done
echo "PULL_WARN health not ready after restart (gateway_ok=$GW_OK agent_api_ok=$API_OK)" >&2
echo "$REV"
EOS
