#!/usr/bin/env bash
# Install the 64-bit Wine bridge the watchdog starts.
#
# A fresh Hostinger image only has 32-bit python.exe and mt5linux 1.1.1.
# terminal64.exe completes IPC with 64-bit C:\Python311\python.exe and the
# pins below. When those imports already succeed, this script does nothing
# except ensure the Linux shim is present.
#
# It does not restart the container and does not change published ports.
# NANOAGENT_BRIDGE_DRY_RUN=1 prints the plan and does not download or install.
set -euo pipefail

CONTAINER="${MT5_CONTAINER:-metatrader-5-ie74-mt5-1}"
WINE_PYTHON="${MT5_WINE_PYTHON:-C:\\Python311\\python.exe}"
PY_VERSION="3.11.9"
PY_URL="https://www.python.org/ftp/python/${PY_VERSION}/python-${PY_VERSION}-amd64.exe"
PY_SHA256="5ee42c4eee1e6b4464bb23722f90b45303f79442df63083f05322f1785f5fdde"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "mt5linux bridge: docker is not installed; skipped" >&2
  exit 0
fi

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "mt5linux bridge: container ${CONTAINER} is not running; skipped" >&2
  exit 0
fi

linux_pins_ok() {
  docker exec -u abc -e HOME=/config "$CONTAINER" python3 -c \
    'import importlib.metadata as m
need={"mt5linux":"0.2.4","rpyc":"5.2.3"}
raise SystemExit(0 if all(m.version(name)==ver for name, ver in need.items()) else 1)'
}

wine_pins_ok() {
  docker exec -u abc \
    -e HOME=/config \
    -e WINEPREFIX=/config/.wine \
    -e WINEDEBUG=-all \
    -e DISPLAY="${MT5_BRIDGE_DISPLAY:-:1}" \
    "$CONTAINER" \
    wine "$WINE_PYTHON" -c \
    'import importlib.metadata as m
need={"numpy":"1.26.4","MetaTrader5":"5.0.6231","mt5linux":"0.2.4","rpyc":"5.2.3"}
raise SystemExit(0 if all(m.version(name)==ver for name, ver in need.items()) else 1)'
}

install_linux_pins() {
  echo "mt5linux bridge: installing Linux mt5linux 0.2.4"
  docker exec -u abc -e HOME=/config -e PIP_DISABLE_PIP_VERSION_CHECK=1 "$CONTAINER" \
    python3 -m pip install --user 'mt5linux==0.2.4' 'rpyc==5.2.3'
}

install_wine_python() {
  local tmpdir archive
  tmpdir="$(mktemp -d)"
  archive="${tmpdir}/python-${PY_VERSION}-amd64.exe"
  echo "mt5linux bridge: installing 64-bit Python ${PY_VERSION} inside the container"
  curl -fsSL "$PY_URL" -o "$archive"
  echo "${PY_SHA256}  ${archive}" | sha256sum -c -
  docker cp "$archive" "${CONTAINER}:/tmp/python-${PY_VERSION}-amd64.exe"
  rm -rf "$tmpdir"
  docker exec -u abc \
    -e HOME=/config \
    -e WINEPREFIX=/config/.wine \
    -e WINEDEBUG=-all \
    -e DISPLAY="${MT5_BRIDGE_DISPLAY:-:1}" \
    "$CONTAINER" \
    wine "/tmp/python-${PY_VERSION}-amd64.exe" \
    /quiet InstallAllUsers=1 PrependPath=1 "TargetDir=C:\\Python311" \
    Include_test=0 Include_doc=0 Include_launcher=0
  docker exec "$CONTAINER" rm -f "/tmp/python-${PY_VERSION}-amd64.exe"
  echo "mt5linux bridge: installing pinned Wine packages"
  docker exec -u abc \
    -e HOME=/config \
    -e WINEPREFIX=/config/.wine \
    -e WINEDEBUG=-all \
    -e DISPLAY="${MT5_BRIDGE_DISPLAY:-:1}" \
    -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$CONTAINER" \
    wine "$WINE_PYTHON" -m pip install --upgrade pip
  docker exec -u abc \
    -e HOME=/config \
    -e WINEPREFIX=/config/.wine \
    -e WINEDEBUG=-all \
    -e DISPLAY="${MT5_BRIDGE_DISPLAY:-:1}" \
    -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
    "$CONTAINER" \
    wine "$WINE_PYTHON" -m pip install \
    'numpy==1.26.4' 'MetaTrader5==5.0.6231' 'mt5linux==0.2.4' 'rpyc==5.2.3'
}

if linux_pins_ok && wine_pins_ok; then
  bash "$ROOT/scripts/install-mt5linux-shim.sh"
  echo "mt5linux bridge: pinned packages already installed"
  exit 0
fi

if [[ "${NANOAGENT_BRIDGE_DRY_RUN:-0}" == 1 ]]; then
  echo "mt5linux bridge: would install 64-bit Python ${PY_VERSION} and the pinned packages"
  exit 0
fi

if ! linux_pins_ok; then
  install_linux_pins
fi
if ! wine_pins_ok; then
  install_wine_python
fi
if ! linux_pins_ok || ! wine_pins_ok; then
  echo "mt5linux bridge: pinned packages are still missing after install" >&2
  exit 1
fi
bash "$ROOT/scripts/install-mt5linux-shim.sh"
echo "mt5linux bridge: installed. The watchdog starts it on the next check."
