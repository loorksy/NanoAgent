#!/usr/bin/env bash
# §11 row 13: local SDK activity tests (CI proxy) + operator notes for device UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== row 13 CI proxy (SDK + pipe; not production §11 closure) =="
bash "$ROOT/scripts/mokli_upgrade_section11_row13_ci.sh"

cat <<'NOTE'

§11 row 13 (mobile) — production requires live device/SDK session:
  1. Pair the Mokli mobile app to the production gateway; send a chat that triggers tools or a structured card.
  2. On VPS after the run completes, export that session:
       bash scripts/vps_section11_row13_export_session.sh 13-mobile.jsonl [session-id]
     (omit session-id to use the most recently updated session — verify it is the phone chat.)
  3. Expand activity row on device: inputs + result visible (packages/mokli-sdk activityLine).
  4. Screenshot on phone; pull artifacts: bash scripts/vps_section11_pull_events.sh
  5. CI only: pytest tests/deploy/test_mokli_pipe.py::test_activity_projection_matches_real_events

NOTE
