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

echo "== §11 init smoke (temp dir; no LLM) =="
INIT_WORK="${TMPDIR:-/tmp}/mokli-section11-init-smoke-$$"
mkdir -p "$INIT_WORK"
bash scripts/mokli_upgrade_section11_init.sh \
  --dir "$INIT_WORK/events" \
  --results "$INIT_WORK/results.json" \
  --require-through 2
rm -rf "$INIT_WORK"

PY="${ROOT}/.venv/bin/pytest"
if [[ ! -x "$PY" ]]; then
  PY=pytest
fi

echo "== pytest scripts/ (excluding this smoke harness) =="
"$PY" tests/scripts/ -q --ignore=tests/scripts/test_mokli_upgrade_operator_smoke.py

echo "== §11 row 13 CI proxy (pipe + mokli-sdk; not production closure) =="
bash scripts/mokli_upgrade_section11_row13_ci.sh

echo "== §11 blockers (local artifacts, --skip-vps; expect BLOCKED until row 13 live) =="
if bash scripts/mokli_upgrade_section11_blockers.sh --skip-vps; then
  echo "NOTE blockers clear — production §11 may be closable" >&2
else
  echo "NOTE blockers reported gaps (expected until VPS live rows 11–13; PARTIAL rejected at 13)" >&2
fi

if [[ -d "$ROOT/section11-events" && -f "$ROOT/section11-results-partial.json" ]]; then
  echo "== §11 partial pack rows 1–10 (--skip-vps) =="
  if bash scripts/mokli_upgrade_section11_blockers.sh \
    --skip-vps --require-through 10 \
    "$ROOT/section11-events" "$ROOT/section11-results-partial.json"; then
    echo "OK local §11 artifacts through row 10 (PARTIAL rows OK in results JSON)"
  else
    echo "WARN §11 rows 1–10 validation failed — sync_from_vps or fix artifacts" >&2
    fail=1
  fi
  echo "== §11 production gate @10 (skip quota/OANDA/pull) =="
  if bash scripts/mokli_upgrade_section11_production_gate.sh \
    --skip-quota --skip-oanda --skip-pull --require-through 10; then
    echo "OK production_gate @10 (artifact pack; not live closure @13)"
  else
    echo "WARN production_gate @10 failed — sync_from_vps or fix artifacts" >&2
    fail=1
  fi
  echo "== §11 timer wake dry-run (cached quota + closure chain preview @13) =="
  bash scripts/mokli_upgrade_section11_timer_wake.sh --dry-run \
    || echo "NOTE timer_wake @13 blocked until live rows + after-p0 (expected)" >&2
fi

if [[ "$fail" -ne 0 ]]; then
  echo "WARN operator smoke: preflight reported failures (dry-run + scripts pytest OK)" >&2
  exit 1
fi

echo "OK operator smoke (preflight + §11 dry-run + init smoke + scripts pytest)"
echo "Tip: timer_wake --dry-run; after reset: timer_wake --wait-quota; operator_unblock --pull-vps (live @13)"
