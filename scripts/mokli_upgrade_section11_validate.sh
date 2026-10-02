#!/usr/bin/env bash
# Wrapper for mokli_upgrade_section11_validate.py (uses repo .venv when present).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

ARGS=("$@")
EVENTS="$ROOT/section11-events"
idx=0
while [[ $idx -lt ${#ARGS[@]} ]]; do
  if [[ "${ARGS[$idx]}" == "--dir" && $((idx + 1)) -lt ${#ARGS[@]} ]]; then
    EVENTS="${ARGS[$idx + 1]}"
  fi
  idx=$((idx + 1))
done
section11_prune_row5_stale_no_nested "$EVENTS" "$ROOT"

exec "$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" "${ARGS[@]}"
