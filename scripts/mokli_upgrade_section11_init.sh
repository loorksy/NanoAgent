#!/usr/bin/env bash
# Scaffold §11 operator artifacts (no LLM). Safe to re-run; does not overwrite results.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

EVENTS="./section11-events"
RESULTS="./section11-results.json"
REQUIRE=13

usage() {
  echo "Usage: $0 [--dir EVENTS] [--results JSON] [--require-through N]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) EVENTS="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --require-through) REQUIRE="$2"; shift 2 ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

mkdir -p "$EVENTS"
if [[ ! -f "$RESULTS" ]]; then
  cp "${ROOT}/docs/section11-results.example.json" "$RESULTS"
  echo "Created $RESULTS from docs/section11-results.example.json"
else
  echo "Keeping existing $RESULTS"
fi

echo "== §11 scaffold =="
echo "  events dir: $EVENTS"
echo "  results:    $RESULTS"
echo "  target rows: 1..${REQUIRE}"
echo ""
echo "Save live JSONL as ${EVENTS}/01-no-tools.jsonl … ${REQUIRE}-….jsonl (see operator-handoff)."
echo ""
echo "== validate (expected incomplete until live runs) =="
set +e
bash "${ROOT}/scripts/mokli_upgrade_section11_validate.sh" \
  --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE"
code=$?
set -e
if [[ "$code" -eq 0 ]]; then
  echo "OK §11 scaffold: all required rows ready — run section11_close.sh"
else
  echo "INFO §11 scaffold: fill missing rows, then validate again and section11_close.sh --apply"
fi
exit 0
