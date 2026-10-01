#!/usr/bin/env bash
# Exercise §11 extract → validate → batch on repo fixture (no LLM, no broker).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

WORK="${TMPDIR:-/tmp}/mokli-section11-dry-run-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

FIXTURE="${ROOT}/tests/fixtures/section11_turn_diagnostics_sample.jsonl"
if [[ ! -f "$FIXTURE" ]]; then
  echo "FAIL missing fixture: $FIXTURE" >&2
  exit 1
fi

cp "$FIXTURE" "$WORK/01-no-tools.jsonl"
cat >"$WORK/section11-results.json" <<'JSON'
{
  "1": "DRY-RUN — fixture only; replace after live §11 row 1"
}
JSON

echo "== extract (fixture) =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_diagnostic_extract.py" --file "$WORK/01-no-tools.jsonl"

echo "== validate row 1 =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$WORK" \
  --results "$WORK/section11-results.json" \
  --require-through 1

echo "== batch markdown (row 1) =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_batch.py" \
  --dir "$WORK" \
  --results "$WORK/section11-results.json" \
  --markdown

echo "OK §11 dry-run (fixture row 1 — not production closure)"
