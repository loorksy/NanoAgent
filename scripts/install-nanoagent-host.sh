#!/usr/bin/env bash
# Reproduce the Mokli host layout under /opt/nanoagent.
#
# Runtime secrets stay on the host: .env, mokli-ui.env, and .mokli/.
# This script never prints those files and never overwrites them.
# It does not install into /opt/mokli and does not change MT5 published ports.
#
# First host:
#   sudo NANOAGENT_BOOTSTRAP=1 scripts/install-nanoagent-host.sh
# Fill the two env files, then:
#   sudo NANOAGENT_RESTART=1 scripts/install-nanoagent-host.sh
#
# NANOAGENT_REF defaults to main, which is the branch the live host tracks.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "install: run as root" >&2
  exit 1
fi

INSTALL_DIR="${NANOAGENT_DIR:-/opt/nanoagent}"
REF="${NANOAGENT_REF:-main}"
REPO="${NANOAGENT_REPO:-https://github.com/loorksy/NanoAgent.git}"
SERVICE_USER="${NANOAGENT_USER:-nanoagent}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$INSTALL_DIR" == "/opt/mokli" ]]; then
  echo "install: refusing /opt/mokli; this host uses ${INSTALL_DIR}" >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  if [[ "$ROOT" != "$INSTALL_DIR" && "${NANOAGENT_BOOTSTRAP:-0}" == 1 ]]; then
    git clone --branch "$REF" "$REPO" "$INSTALL_DIR"
  elif [[ "$ROOT" != "$INSTALL_DIR" ]]; then
    echo "install: ${INSTALL_DIR} has no checkout. Re-run with NANOAGENT_BOOTSTRAP=1" >&2
    exit 1
  fi
fi

if [[ -d "$INSTALL_DIR/.git" && "$INSTALL_DIR" != "$ROOT" ]]; then
  git -C "$INSTALL_DIR" fetch origin "$REF"
  git -C "$INSTALL_DIR" checkout "$REF"
  git -C "$INSTALL_DIR" merge --ff-only "origin/${REF}"
fi

SOURCE="$INSTALL_DIR"
if [[ ! -f "$SOURCE/scripts/systemd/nanoagent-gateway.service" ]]; then
  SOURCE="$ROOT"
fi

install -m 0755 "$SOURCE/scripts/mt5linux-bridge-watchdog.sh" /usr/local/sbin/mt5linux-bridge-watchdog.sh
install -m 0644 "$SOURCE/scripts/systemd/nanoagent-gateway.service" /etc/systemd/system/nanoagent-gateway.service
install -m 0644 "$SOURCE/scripts/systemd/nanoagent-open-webui.service" /etc/systemd/system/nanoagent-open-webui.service
install -m 0644 "$SOURCE/scripts/systemd/mt5linux-bridge-watchdog.service" /etc/systemd/system/mt5linux-bridge-watchdog.service
install -m 0644 "$SOURCE/scripts/systemd/mt5linux-bridge-watchdog.timer" /etc/systemd/system/mt5linux-bridge-watchdog.timer

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  install -m 0600 -o "$SERVICE_USER" -g "$SERVICE_USER" "$SOURCE/.env.example" "$INSTALL_DIR/.env"
  echo "install: created ${INSTALL_DIR}/.env from the example. Fill it before starting."
fi
if [[ ! -f "$INSTALL_DIR/mokli-ui.env" ]]; then
  install -m 0600 -o "$SERVICE_USER" -g "$SERVICE_USER" \
    "$SOURCE/deploy/nanoagent/mokli-ui.env.example" "$INSTALL_DIR/mokli-ui.env"
  echo "install: created ${INSTALL_DIR}/mokli-ui.env from the example. Fill it before starting."
fi

if [[ -d /docker/traefik/dynamic && ! -f /docker/traefik/dynamic/nanoagent.yml ]]; then
  install -m 0644 "$SOURCE/deploy/traefik/nanoagent.yml" /docker/traefik/dynamic/nanoagent.yml
  echo "install: added the Traefik route. Edit the Host rule, then reload Traefik."
fi

if [[ "${NANOAGENT_BOOTSTRAP:-0}" == 1 ]]; then
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install -U pip
  "$INSTALL_DIR/.venv/bin/pip" install -e "${INSTALL_DIR}[trading-mt5]"
  python3 -m venv "$INSTALL_DIR/mokli-ui/backend/.venv"
  "$INSTALL_DIR/mokli-ui/backend/.venv/bin/pip" install -U pip
  "$INSTALL_DIR/mokli-ui/backend/.venv/bin/pip" install -e "$INSTALL_DIR/mokli-ui"
  if command -v npm >/dev/null 2>&1; then
    (cd "$INSTALL_DIR/mokli-ui" && npm ci && NODE_OPTIONS=--max-old-space-size=8192 npm run build)
  else
    echo "install: npm is missing. Build mokli-ui elsewhere and copy mokli-ui/build here." >&2
  fi
  if docker inspect -f '{{.State.Running}}' "${MT5_CONTAINER:-metatrader-5-ie74-mt5-1}" >/dev/null 2>&1; then
    bash "$SOURCE/scripts/install-mt5linux-shim.sh"
  fi
  chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
fi

systemctl daemon-reload
systemctl enable nanoagent-gateway.service nanoagent-open-webui.service mt5linux-bridge-watchdog.timer
if [[ "${NANOAGENT_RESTART:-0}" == 1 ]]; then
  systemctl restart nanoagent-gateway.service nanoagent-open-webui.service
  systemctl start mt5linux-bridge-watchdog.timer
fi

echo "install: units are in place. Secrets remain only in ${INSTALL_DIR}/.env and mokli-ui.env."
