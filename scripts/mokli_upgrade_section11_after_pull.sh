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

BASELINE="${EVENTS}/01-no-tools.jsonl"
AFTER_P0="${EVENTS}/01-no-tools-after-p0.jsonl"
QUOTA_PROBE="${EVENTS}/quota-probe.jsonl"
if [[ -f "$BASELINE" && -f "$AFTER_P0" ]]; then
  echo ""
  echo "== P0 live delta (row 1 after) =="
  bash "${ROOT}/scripts/mokli_upgrade_p0_live_delta.sh" "$BASELINE" "$AFTER_P0"
elif [[ -f "$BASELINE" && -f "$QUOTA_PROBE" ]]; then
  echo ""
  echo "== P0 interim (quota-probe vs row 1; in=0 when quota blocked) =="
  bash "${ROOT}/scripts/mokli_upgrade_p0_live_delta.sh" "$BASELINE" "$QUOTA_PROBE"
  echo "NOTE: rerun row 1 after credits → 01-no-tools-after-p0.jsonl for authoritative delta_in"
fi
