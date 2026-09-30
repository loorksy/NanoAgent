#!/usr/bin/env bash
# Local operator smoke: preflight (best-effort), §11 dry-run, scripts pytest.
# Does not call LLM/broker; does not close production §11.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

echo "== preflight (API/config; may FAIL if services down) =="
if bash scripts/mokli_upgrade_preflight.sh; then
  :
else
  fail=1
fi

echo "== §11 dry-run (fixture row 1) =="
bash scripts/mokli_upgrade_section11_dry_run.sh

PY="${ROOT}/.venv/bin/pytest"
if [[ ! -x "$PY" ]]; then
  PY=pytest
fi

echo "== pytest scripts/ (excluding this smoke harness) =="
"$PY" tests/scripts/ -q --ignore=tests/scripts/test_mokli_upgrade_operator_smoke.py

if [[ "$fail" -ne 0 ]]; then
  echo "WARN operator smoke: preflight reported failures (dry-run + scripts pytest OK)" >&2
  exit 1
fi

echo "OK operator smoke (preflight + §11 dry-run + scripts pytest)"
