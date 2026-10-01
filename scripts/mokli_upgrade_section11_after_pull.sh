#!/usr/bin/env bash
# After vps_section11_pull_events.sh: validate partial rows + print P0 baseline table.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

EVENTS="${1:-$ROOT/section11-events}"
RESULTS="${2:-$ROOT/section11-results-partial.json}"
REQUIRE="${3:-10}"

bash "${ROOT}/scripts/mokli_upgrade_section11_status.sh" \
  --skip-quota --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"

echo ""
echo "== P0 baseline (§2.1) from JSONL =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_diagnostic_extract.py" --p0-baseline "$EVENTS"
