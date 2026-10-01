#!/usr/bin/env bash
# Print §11 artifact readiness (local or after vps_section11_pull_events.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

EVENTS="${1:-$ROOT/section11-events}"
RESULTS="${2:-$ROOT/section11-results-partial.json}"
REQUIRE="${3:-13}"

if [[ ! -f "$RESULTS" ]]; then
  echo "WARN: results file missing: $RESULTS (copy from docs/section11-results.example.json)" >&2
  exit 1
fi

echo "== §11 status (events=$EVENTS require-through=$REQUIRE) =="
"$PYTHON" "${ROOT}/scripts/mokli_upgrade_section11_validate.py" \
  --dir "$EVENTS" --results "$RESULTS" --require-through "$REQUIRE" || true

if [[ -n "${MOKLI_SSH_HOST:-}" ]] || [[ -n "${VPS:-}" ]]; then
  echo "== VPS LLM quota probe (optional) =="
  if bash "${ROOT}/scripts/vps_section11_quota_probe.sh" "quota-status-$(date +%s).jsonl"; then
    echo "LLM: ready for live §11 turns"
  else
    echo "LLM: blocked (see operator handoff — credits or preset)"
  fi
fi
