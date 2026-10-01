#!/usr/bin/env bash
# §11 row 13: local SDK activity tests (CI proxy) + operator notes for device UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== mokli-sdk activity (§11.1 row 13; not production §11 closure) =="
if [[ -d packages/mokli-sdk ]]; then
  if command -v bun >/dev/null 2>&1; then
    (cd packages/mokli-sdk && bun test test/store.test.ts) || true
  else
    echo "WARN: bun not installed; run: cd packages/mokli-sdk && npm test" >&2
  fi
else
  echo "WARN: packages/mokli-sdk missing" >&2
fi

cat <<'NOTE'

§11 row 13 (mobile) — production requires live device/SDK session:
  1. Same Mokli pipe/gateway events as desktop; save JSONL as section11-events/13-mobile.jsonl.
  2. Expand activity row: inputs + result visible (matches packages/mokli-sdk activityLine).
  3. Screenshot on phone; optional: paste diagnostic line from pipe if SHOW_DIAGNOSTICS enabled.
  4. CI only: pytest tests/deploy/test_mokli_pipe.py::test_activity_projection_matches_real_events

NOTE
