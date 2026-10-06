#!/usr/bin/env bash
# §11 row 13 CI proxy: SDK activity + pipe projection (no device, no LLM).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/pytest"
[[ -x "$PY" ]] || PY=pytest

echo "== pipe activity projection (real event fixtures) =="
"$PY" tests/deploy/test_mokli_pipe.py::test_activity_projection_matches_real_events -q

echo "== mokli-sdk activityLine / SessionStore =="
if [[ ! -d packages/mokli-sdk ]]; then
  echo "ERROR packages/mokli-sdk missing" >&2
  exit 1
fi
if command -v bun >/dev/null 2>&1; then
  (cd packages/mokli-sdk && bun test test/store.test.ts)
else
  echo "ERROR bun required for row 13 CI proxy" >&2
  exit 1
fi

echo "OK §11 row 13 CI proxy (device JSONL still required for production closure)"
