#!/usr/bin/env bash
# Install the wine-bridge shim into the MT5 container.
# The Hostinger image starts `python3 -m mt5linux -w wine python.exe`.
# mt5linux 0.2.4 does not understand -w, so this file re-executes under Wine.
# Published container ports are not changed and the container is not restarted.
set -euo pipefail

CONTAINER="${MT5_CONTAINER:-metatrader-5-ie74-mt5-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/scripts/mt5linux/__main__.py"
DEST="/config/.local/lib/python3.11/site-packages/mt5linux/__main__.py"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "mt5linux shim: container ${CONTAINER} is not running" >&2
  exit 1
fi

discovered="$(
  docker exec -u abc -e HOME=/config "$CONTAINER" python3 -c \
    'import mt5linux, pathlib; print(pathlib.Path(mt5linux.__file__).resolve().parent / "__main__.py")' \
    2>/dev/null || true
)"
if [[ -n "$discovered" ]]; then
  DEST="$discovered"
fi

if docker exec "$CONTAINER" python3 -c "from pathlib import Path; raise SystemExit(0 if 'wine bridge shim' in Path('${DEST}').read_text(encoding='utf-8', errors='replace') else 1)"; then
  echo "mt5linux shim: already installed"
  exit 0
fi

docker cp "$SRC" "${CONTAINER}:${DEST}"
echo "mt5linux shim: installed. The watchdog starts the bridge on the next check."
