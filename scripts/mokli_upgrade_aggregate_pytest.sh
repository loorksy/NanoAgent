#!/usr/bin/env bash
# Same aggregate target as AGENTS.md / completion audit (no LLM).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/pytest"
[[ -x "$PY" ]] || PY=pytest

exec "$PY" tests/agent tests/trading tests/agent_api tests/deploy/test_mokli_pipe.py tests/scripts/ -q "$@"
