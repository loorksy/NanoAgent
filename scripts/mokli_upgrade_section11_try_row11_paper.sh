#!/usr/bin/env bash
# Run §11 row 11 (paper via Agent API) when VPS quota + OANDA are ready; no-op otherwise.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota --require-oanda >/dev/null 2>&1; then
  echo "SKIP §11 row 11: need live quota (in>0) and OANDA on VPS" >&2
  exit 0
fi

echo "== §11 row 11 paper (Agent API) =="
bash "$ROOT/scripts/vps_section11_row11_paper.sh"
