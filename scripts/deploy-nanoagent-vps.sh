#!/usr/bin/env bash
# Deploy NanoAgent gold trading gateway to VPS in isolation from other projects.
# Does NOT modify foxagent, aichart, zorroagent, or other /opt/* trees.
#
# Required env: VPS, VPSPASS
# Optional: NANOAGENT_DOMAIN (default nanoagent.lork.cloud)
#           NANOAGENT_BRANCH (default cursor/gold-trading-chat-first-aba3)
#           NANOAGENT_WEB_TOKEN (auto-generated if unset)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${NANOAGENT_DOMAIN:-nanoagent.lork.cloud}"
BRANCH="${NANOAGENT_BRANCH:-main}"
INSTALL_DIR="/opt/nanoagent"
SERVICE_USER="nanoagent"
WEB_PORT=8766
HEALTH_PORT=18791
REPO_URL="https://github.com/loorksy/NanoAgent.git"

if [[ -z "${VPS:-}" || -z "${VPSPASS:-}" ]]; then
  echo "deploy: VPS and VPSPASS must be set" >&2
  exit 1
fi

command -v sshpass >/dev/null || { echo "deploy: sshpass required" >&2; exit 1; }

WEB_TOKEN="${NANOAGENT_WEB_TOKEN:-$(openssl rand -hex 24)}"

REMOTE_SCRIPT=$(cat <<'EOS'
set -euo pipefail
INSTALL_DIR="$1"
SERVICE_USER="$2"
WEB_PORT="$3"
HEALTH_PORT="$4"
DOMAIN="$5"
BRANCH="$6"
REPO_URL="$7"
WEB_TOKEN="$8"

id "$SERVICE_USER" &>/dev/null || useradd --system --home "$INSTALL_DIR" --shell /bin/bash "$SERVICE_USER"

mkdir -p "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

git_safe() {
  sudo -u "$SERVICE_USER" git -C "$INSTALL_DIR" "$@"
}

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  sudo -u "$SERVICE_USER" git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
else
  git_safe config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true
  git_safe fetch --depth 1 origin "$BRANCH"
  git_safe checkout -B "$BRANCH" FETCH_HEAD
fi

cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" python3 -m venv .venv
sudo -u "$SERVICE_USER" bash -lc "cd '$INSTALL_DIR' && source .venv/bin/activate && pip install -U pip wheel && pip install -e ."

# OANDA from foxagent (read-only)
if [[ -f scripts/sync-oanda-from-foxagent.sh ]]; then
  bash scripts/sync-oanda-from-foxagent.sh || true
fi

if ! sudo -u "$SERVICE_USER" bash -lc 'command -v bun >/dev/null'; then
  sudo -u "$SERVICE_USER" bash -lc 'curl -fsSL https://bun.sh/install | bash'
fi
sudo -u "$SERVICE_USER" bash -lc "cd '$INSTALL_DIR/webui' && export PATH=\"\$HOME/.bun/bin:\$PATH\" && bun install && bun run build"
cd "$INSTALL_DIR"

CONFIG_DIR="$INSTALL_DIR/.nanobot"
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
  sudo -u "$SERVICE_USER" HOME="$INSTALL_DIR" "$INSTALL_DIR/.venv/bin/nanobot" onboard --yes 2>/dev/null || true
fi

python3 - "$CONFIG_DIR/config.json" "$WEB_PORT" "$HEALTH_PORT" "$WEB_TOKEN" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
web_port, health_port, token = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
cfg = {}
if path.exists():
    cfg = json.loads(path.read_text())
cfg.setdefault("gateway", {})["host"] = "0.0.0.0"
cfg["gateway"]["port"] = health_port
cfg.setdefault("channels", {}).setdefault("websocket", {})
ws = cfg["channels"]["websocket"]
ws["enabled"] = True
ws["host"] = "0.0.0.0"
ws["port"] = web_port
existing = ws.get("tokenIssueSecret")
ws["tokenIssueSecret"] = existing or token
tools = cfg.setdefault("tools", {})
tools["webuiAllowRemotePackageInstall"] = True
print("ISSUED_TOKEN=" + ws["tokenIssueSecret"])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(cfg, indent=2) + "\n")
PY

sudo -u "$SERVICE_USER" bash -lc "cd '$INSTALL_DIR' && source .venv/bin/activate && pip install -U \
  'python-telegram-bot[socks,webhooks]>=22.6,<23.0' \
  'socksio>=1.0.0,<2.0.0' \
  'python-socks[asyncio]>=2.8.0,<3.0.0' \
  'neonize>=0.4.3.post0,<0.5.0' \
  'segno>=1.6.1,<2.0.0'"
chown -R "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR"

cat > /etc/systemd/system/nanoagent-gateway.service <<UNIT
[Unit]
Description=NanoAgent Gold Trading Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin:/usr/bin:/bin
Environment=HOME=$INSTALL_DIR
EnvironmentFile=-$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/nanobot gateway --foreground --port $HEALTH_PORT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable nanoagent-gateway.service
systemctl restart nanoagent-gateway.service

cat > /etc/nginx/sites-available/nanoagent.lork.cloud <<NGX
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 3600s;
    }
}
NGX

ln -sf /etc/nginx/sites-available/nanoagent.lork.cloud /etc/nginx/sites-enabled/nanoagent.lork.cloud
nginx -t && systemctl reload nginx

if ! command -v certbot >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq certbot python3-certbot-nginx || true
fi
if command -v certbot >/dev/null; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect --keep-until-expiring || true
  nginx -t && systemctl reload nginx || true
fi

echo "DEPLOY_OK domain=$DOMAIN web_port=$WEB_PORT"
EOS
)

echo "Deploying NanoAgent to ${VPS} (${DOMAIN})..."
OUT=$(sshpass -p "$VPSPASS" ssh -o StrictHostKeyChecking=no "root@${VPS}" \
  "bash -s" -- "$INSTALL_DIR" "$SERVICE_USER" "$WEB_PORT" "$HEALTH_PORT" "$DOMAIN" "$BRANCH" "$REPO_URL" "$WEB_TOKEN" <<< "$REMOTE_SCRIPT")

echo "$OUT"
echo ""
echo "WebUI: https://${DOMAIN}/#/connect"
ISSUED=$(printf '%s\n' "$OUT" | awk -F= '/^ISSUED_TOKEN=/{print $2}' | tail -1)
echo "Bootstrap token (save this): ${ISSUED:-$WEB_TOKEN}"
