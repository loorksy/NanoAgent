#!/usr/bin/env bash
# After vps_section11_pull_events.sh: validate partial rows + print P0 baseline table.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

EVENTS="${1:-$ROOT/section11-events}"
RESULTS="${2:-$ROOT/section11-results-partial.json}"
REQUIRE="${3:-10}"

set +e
bash "${ROOT}/scripts/mokli_upgrade_section11_status.sh" \
  --skip-quota --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"
STATUS_EC=$?
set -e
if [[ "$STATUS_EC" -ne 0 ]]; then
  echo "WARN: §11 status incomplete (require-through=$REQUIRE) — continuing P0 table/delta" >&2
fi

echo ""
echo "== P0 baseline (§2.1) from JSONL =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_diagnostic_extract.py" --p0-baseline "$EVENTS"

AFTER_P0="${EVENTS}/01-no-tools-after-p0.jsonl"
QUOTA_PROBE="${EVENTS}/quota-probe.jsonl"
P0_SUMMARY="${EVENTS}/p0-interim-summary.txt"
BASELINE=""
if [[ -f "${EVENTS}/01-no-tools.jsonl" ]]; then
  BASELINE="${EVENTS}/01-no-tools.jsonl"
else
  BASELINE="$("$PYTHON" "${ROOT}/scripts/mokli_upgrade_diagnostic_extract.py" \
    --resolve-row 1 --dir "$EVENTS" --exclude-stem after-p0 2>/dev/null || true)"
fi
if [[ -n "$BASELINE" && -f "$BASELINE" && -f "$AFTER_P0" ]]; then
  echo ""
  echo "== P0 live delta (row 1 after) =="
  {
    echo "# P0 live delta $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    bash "${ROOT}/scripts/mokli_upgrade_p0_live_delta.sh" "$BASELINE" "$AFTER_P0"
  } | tee "$P0_SUMMARY"
elif [[ -n "$BASELINE" && -f "$BASELINE" && -f "$QUOTA_PROBE" ]]; then
  echo ""
  echo "== P0 interim (quota-probe vs row 1; in=0 when quota blocked) =="
  {
    echo "# P0 interim (not authoritative for delta_in when quota blocked)"
    echo "# generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    bash "${ROOT}/scripts/mokli_upgrade_p0_live_delta.sh" "$BASELINE" "$QUOTA_PROBE"
    echo "NOTE: rerun row 1 after credits → 01-no-tools-after-p0.jsonl for authoritative delta_in"
  } | tee "$P0_SUMMARY"
fi

echo ""
echo "== P0 local estimate (no LLM; compare to VPS row 1 in=10934 baseline) =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_p0_turn_estimate.py" --compare "مرحبا" "حلل الذهب" \
  || echo "WARN: mokli_upgrade_p0_turn_estimate.py failed" >&2
