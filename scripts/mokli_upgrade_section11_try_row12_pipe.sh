#!/usr/bin/env bash
# Run §11 row 12 (Mokli pipe JSONL) when VPS quota is ready; no-op otherwise.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENTS="${MOKLI_SECTION11_EVENTS:-$ROOT/section11-events}"
TARGET="$EVENTS/12-desktop-ui.jsonl"

if [[ -f "$TARGET" ]] && grep -qE 'structured|decision' "$TARGET" 2>/dev/null; then
  echo "SKIP §11 row 12: $TARGET already has structured/decision events" >&2
  exit 0
fi

if ! bash "$ROOT/scripts/vps_section11_env_check.sh" --require-quota >/dev/null 2>&1; then
  echo "SKIP §11 row 12: need live quota (in>0) on VPS" >&2
  exit 0
fi

echo "== §11 row 12 pipe (headless Mokli pipe → gateway JSONL) =="
bash "$ROOT/scripts/vps_section11_row12_pipe_turn.sh"
