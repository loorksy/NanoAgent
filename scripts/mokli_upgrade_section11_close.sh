#!/usr/bin/env bash
# After live §11 JSONL + section11-results.json: validate → batch markdown → patch report.
# Default is dry-run patch only; pass --apply to write docs/mokli-agent-upgrade-report.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

EVENTS="./section11-events"
RESULTS="./section11-results.json"
REPORT="${ROOT}/docs/mokli-agent-upgrade-report.md"
REQUIRE=13
APPLY=0

usage() {
  echo "Usage: $0 [--dir EVENTS] [--results JSON] [--report PATH] [--require-through N] [--apply]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) EVENTS="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --require-through) REQUIRE="$2"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

echo "== validate rows 1..${REQUIRE} =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"

echo "== batch markdown =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_batch.py" \
  --dir "$EVENTS" --results "$RESULTS" --markdown

PATCH_ARGS=(
  "$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_patch_report.py"
  --dir "$EVENTS"
  --results "$RESULTS"
  --report "$REPORT"
  --require-through "$REQUIRE"
  --skip-validate
)

if [[ "$APPLY" -eq 1 ]]; then
  echo "== patch report (write) =="
  "${PATCH_ARGS[@]}"
  echo "OK §11 close: report updated at $REPORT"
  CANONICAL_REPORT="${ROOT}/docs/mokli-agent-upgrade-report.md"
  REPORT_ABS="$(readlink -f "$REPORT")"
  CANONICAL_ABS="$(readlink -f "$CANONICAL_REPORT")"
  if [[ "$REQUIRE" -ge 13 && "$REPORT_ABS" == "$CANONICAL_ABS" ]]; then
    PYTEST="${ROOT}/.venv/bin/pytest"
    if [[ ! -x "$PYTEST" ]]; then
      PYTEST=pytest
    fi
    echo "== §11 report gate (canonical report) =="
    "$PYTEST" "${ROOT}/tests/scripts/test_mokli_upgrade_report_section11_gate.py" -q
    echo "OK §11 report gate"
  fi
else
  echo "== patch report (dry-run) =="
  "${PATCH_ARGS[@]}" --dry-run
  echo "INFO re-run with --apply to write $REPORT"
fi
