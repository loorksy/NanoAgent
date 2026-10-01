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
ALLOW_PARTIAL=0

usage() {
  echo "Usage: $0 [--dir EVENTS] [--results JSON] [--report PATH] [--require-through N] [--allow-partial] [--apply]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) EVENTS="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --require-through) REQUIRE="$2"; shift 2 ;;
    --allow-partial) ALLOW_PARTIAL=1; shift ;;
    --apply) APPLY=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ ! -f "$RESULTS" && -f "${ROOT}/section11-results-partial.json" ]]; then
  echo "INFO: results file missing; using ${ROOT}/section11-results-partial.json" >&2
  RESULTS="${ROOT}/section11-results-partial.json"
fi

if [[ "$APPLY" -eq 1 && "$ALLOW_PARTIAL" -eq 1 ]]; then
  echo "ERROR: --apply cannot be used with --allow-partial (fix PARTIAL rows first)" >&2
  exit 1
fi

VALIDATE_ARGS=(--dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE")
if [[ "$ALLOW_PARTIAL" -eq 1 ]]; then
  VALIDATE_ARGS+=(--allow-partial)
fi

echo "== validate rows 1..${REQUIRE} =="
set +e
VALID_OUT=$(
  bash "${ROOT}/scripts/mokli_upgrade_section11_validate.sh" "${VALIDATE_ARGS[@]}" 2>&1
)
VALID_EC=$?
set -e
printf '%s\n' "$VALID_OUT"
if [[ "$VALID_EC" -ne 0 ]]; then
  echo "HINT: bash scripts/mokli_upgrade_section11_blockers.sh --skip-vps --require-through ${REQUIRE}" >&2
  exit "$VALID_EC"
fi

echo "== batch markdown =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_batch.py" \
  --dir "$EVENTS" --results "$RESULTS" --markdown --require-through "$REQUIRE"

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
  if [[ "$REQUIRE" -ge 13 ]]; then
    CANONICAL_RESULTS="${ROOT}/section11-results.json"
    RESULTS_ABS="$(readlink -f "$RESULTS" 2>/dev/null || true)"
    PARTIAL_ABS="$(readlink -f "${ROOT}/section11-results-partial.json" 2>/dev/null || true)"
    if [[ -n "$RESULTS_ABS" && -n "$PARTIAL_ABS" && "$RESULTS_ABS" == "$PARTIAL_ABS" ]]; then
      cp "$RESULTS_ABS" "$CANONICAL_RESULTS"
      echo "OK promoted partial results → $CANONICAL_RESULTS"
    fi
  fi
else
  echo "== patch report (dry-run) =="
  "${PATCH_ARGS[@]}" --dry-run
  echo "INFO re-run with --apply to write $REPORT"
fi
