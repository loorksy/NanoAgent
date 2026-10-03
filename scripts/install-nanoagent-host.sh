#!/usr/bin/env bash
# Install Mokli on a host so a programmer can run it.
#
# The script installs packages, the checkout, both virtualenvs, the UI build,
# systemd units, the Traefik route file, and the MT5 bridge pins. It creates
# .env and mokli-ui.env from the examples when they are missing, and it never
# overwrites a value a programmer already set.
#
# It does not fill secrets. After it finishes, set the blank keys it lists,
# then start the services with NANOAGENT_RESTART=1. It does not install into
# /opt/mokli and does not change the MT5 container's published ports.
#
#   sudo NANOAGENT_BOOTSTRAP=1 scripts/install-nanoagent-host.sh
#   # fill the keys the script lists
#   sudo NANOAGENT_RESTART=1 scripts/install-nanoagent-host.sh
#
# NANOAGENT_REF defaults to main.
set -euo pipefail

INSTALL_DIR="${NANOAGENT_DIR:-/opt/nanoagent}"
REF="${NANOAGENT_REF:-main}"
REPO="${NANOAGENT_REPO:-https://github.com/loorksy/NanoAgent.git}"
SERVICE_USER="${NANOAGENT_USER:-nanoagent}"
NODE_VERSION="${NANOAGENT_NODE_VERSION:-22.14.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

node_ok() {
  command -v node >/dev/null 2>&1 || return 1
  local major
  major="$(node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)"
  [[ "$major" -ge 18 && "$major" -le 22 ]]
}

ensure_os_packages() {
  if [[ "${NANOAGENT_SKIP_APT:-0}" == 1 ]]; then
    return 0
  fi
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates curl git xz-utils build-essential \
    python3 python3-venv python3-pip python3-dev
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    apt-get install -y --no-install-recommends python3.11 python3.11-venv python3.11-dev
  fi
}

pick_python() {
  if command -v python3.11 >/dev/null 2>&1 \
    && python3.11 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo python3.11
    return 0
  fi
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo python3
    return 0
  fi
  echo "install: Python 3.11 or newer is required" >&2
  return 1
}

ensure_node() {
  if node_ok; then
    return 0
  fi
  local arch tarball sumfile
  case "$(uname -m)" in
    x86_64) arch="linux-x64" ;;
    aarch64 | arm64) arch="linux-arm64" ;;
    *)
      echo "install: unsupported CPU for the Node.js archive: $(uname -m)" >&2
      return 1
      ;;
  esac
  tarball="node-v${NODE_VERSION}-${arch}.tar.xz"
  sumfile="$(mktemp)"
  echo "install: installing Node.js ${NODE_VERSION}"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o "$sumfile"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/${tarball}" -o "/tmp/${tarball}"
  (cd /tmp && grep "  ${tarball}$" "$sumfile" | sha256sum -c -)
  rm -f "$sumfile"
  tar -xJf "/tmp/${tarball}" -C /usr/local --strip-components=1
  rm -f "/tmp/${tarball}"
  node_ok
}

install_python_apps() {
  local py
  py="$(pick_python)"
  "$py" -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install -U pip
  "$INSTALL_DIR/.venv/bin/pip" install -e "${INSTALL_DIR}[trading-mt5]"
  "$py" -m venv "$INSTALL_DIR/mokli-ui/backend/.venv"
  "$INSTALL_DIR/mokli-ui/backend/.venv/bin/pip" install -U pip
  "$INSTALL_DIR/mokli-ui/backend/.venv/bin/pip" install -e "$INSTALL_DIR/mokli-ui"
}

# Point MT5_HOST at the container when the example default is still in place.
# A custom value is left alone. The address is not printed.
wire_mt5_host() {
  local envfile="$1"
  local container="${MT5_CONTAINER:-metatrader-5-ie74-mt5-1}"
  local current="" ip="" tmp
  [[ -f "$envfile" ]] || return 0
  current="$(grep -E '^MT5_HOST=' "$envfile" | tail -1 | cut -d= -f2- || true)"
  current="${current//\"/}"
  current="${current//\'/}"
  current="${current//[[:space:]]/}"
  if [[ -n "$current" && "$current" != "localhost" && "$current" != "127.0.0.1" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "install: MT5_HOST is still localhost. Set it to the MT5 container address."
    return 0
  fi
  ip="$(
    docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' \
      "$container" 2>/dev/null | awk '{print $1}' || true
  )"
  if [[ -z "$ip" ]]; then
    echo "install: MT5_HOST is still localhost. Set it to the MT5 container address."
    return 0
  fi
  tmp="$(mktemp)"
  awk -v addr="$ip" '
    BEGIN { found = 0 }
    /^MT5_HOST=/ { print "MT5_HOST=" addr; found = 1; next }
    { print }
    END { if (!found) print "MT5_HOST=" addr }
  ' "$envfile" >"$tmp"
  cat "$tmp" >"$envfile"
  rm -f "$tmp"
  echo "install: MT5_HOST now points at the MT5 container. The address was not printed."
}

# Print key names that are still blank. Never print the values that are set.
report_blank_keys() {
  local file="$1"
  local note="$2"
  shift 2
  local key value blank=()
  [[ -f "$file" ]] || return 0
  for key in "$@"; do
    value="$(grep -E "^${key}=" "$file" | tail -1 | cut -d= -f2- || true)"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ -z "$value" ]]; then
      blank+=("$key")
    fi
  done
  if ((${#blank[@]})); then
    printf 'install: %s in %s (values are not shown): %s\n' "$note" "$file" "${blank[*]}"
  fi
}

main() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "install: run as root" >&2
    exit 1
  fi
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

  local source="$INSTALL_DIR"
  if [[ ! -f "$source/scripts/systemd/nanoagent-gateway.service" ]]; then
    source="$ROOT"
  fi

  install -m 0755 "$source/scripts/mt5linux-bridge-watchdog.sh" /usr/local/sbin/mt5linux-bridge-watchdog.sh
  install -m 0644 "$source/scripts/systemd/nanoagent-gateway.service" /etc/systemd/system/nanoagent-gateway.service
  install -m 0644 "$source/scripts/systemd/nanoagent-open-webui.service" /etc/systemd/system/nanoagent-open-webui.service
  install -m 0644 "$source/scripts/systemd/mt5linux-bridge-watchdog.service" /etc/systemd/system/mt5linux-bridge-watchdog.service
  install -m 0644 "$source/scripts/systemd/mt5linux-bridge-watchdog.timer" /etc/systemd/system/mt5linux-bridge-watchdog.timer

  if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    install -m 0600 -o "$SERVICE_USER" -g "$SERVICE_USER" "$source/.env.example" "$INSTALL_DIR/.env"
    echo "install: created ${INSTALL_DIR}/.env from the example."
  fi
  if [[ ! -f "$INSTALL_DIR/mokli-ui.env" ]]; then
    install -m 0600 -o "$SERVICE_USER" -g "$SERVICE_USER" \
      "$source/deploy/nanoagent/mokli-ui.env.example" "$INSTALL_DIR/mokli-ui.env"
    echo "install: created ${INSTALL_DIR}/mokli-ui.env from the example."
  fi

  if [[ -d /docker/traefik/dynamic && ! -f /docker/traefik/dynamic/nanoagent.yml ]]; then
    install -m 0644 "$source/deploy/traefik/nanoagent.yml" /docker/traefik/dynamic/nanoagent.yml
    echo "install: added the Traefik route. Edit the Host rule, then reload Traefik."
  fi

  if [[ "${NANOAGENT_BOOTSTRAP:-0}" == 1 ]]; then
    ensure_os_packages
    ensure_node
    install_python_apps
    (cd "$INSTALL_DIR/mokli-ui" && npm ci && NODE_OPTIONS=--max-old-space-size=8192 npm run build)
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
  fi

  bash "$source/scripts/install-mt5linux-bridge.sh"
  wire_mt5_host "$INSTALL_DIR/.env"

  systemctl daemon-reload
  systemctl enable nanoagent-gateway.service nanoagent-open-webui.service mt5linux-bridge-watchdog.timer
  if [[ "${NANOAGENT_RESTART:-0}" == 1 ]]; then
    systemctl restart nanoagent-gateway.service nanoagent-open-webui.service
    systemctl start mt5linux-bridge-watchdog.timer
  fi

  report_blank_keys "$INSTALL_DIR/.env" "optional market-data keys are blank" \
    OANDA_API_TOKEN OANDA_ACCOUNT_ID
  report_blank_keys "$INSTALL_DIR/mokli-ui.env" "set these keys" \
    MOKLI_SECRET_KEY MOKLI_API_TOKEN MT5_DESKTOP_USER MT5_DESKTOP_PASSWORD
  echo "install: units are in place. Secrets stay in ${INSTALL_DIR}/.env and mokli-ui.env."
  echo "install: leave MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER empty so the Connect page owns the account."
  echo "install: MOKLI_API_TOKEN is the gateway admin token at ${INSTALL_DIR}/.mokli/workspace/agent_api/admin_token after the first gateway start. Copy it; do not print it."
  echo "install: MOKLI_SECRET_KEY is a new random value, for example: openssl rand -hex 32"
}

if [[ "${NANOAGENT_INSTALL_LIB_ONLY:-0}" != 1 ]]; then
  main "$@"
fi
