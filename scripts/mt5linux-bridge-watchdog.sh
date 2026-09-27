#!/usr/bin/env bash
# Bring the mt5linux 0.2 bridge back when nothing is listening on port 8001.
# The Hostinger image starts the bridge once from start.sh and does not supervise it.
set -euo pipefail

CONTAINER="${MT5_CONTAINER:-metatrader-5-ie74-mt5-1}"
PORT="${MT5_BRIDGE_PORT:-8001}"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "mt5linux watchdog: container ${CONTAINER} is not running" >&2
  exit 0
fi

if docker exec "$CONTAINER" ss -tuln | grep -q ":${PORT} "; then
  exit 0
fi

# A start is already in progress. Do not launch a second server.
if docker exec "$CONTAINER" ps -eo args | grep -q 'python.exe -m mt5linux'; then
  exit 0
fi

echo "mt5linux watchdog: port ${PORT} is closed; starting the bridge" >&2
docker exec -d -u abc \
  -e HOME=/config \
  -e WINEPREFIX=/config/.wine \
  -e WINEDEBUG=-all \
  -e DISPLAY="${MT5_BRIDGE_DISPLAY:-:1}" \
  "$CONTAINER" \
  bash -c "python3 -m mt5linux --host 0.0.0.0 -p ${PORT} -w wine python.exe >> /config/mt5linux-bridge.log 2>&1"
