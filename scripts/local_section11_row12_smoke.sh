#!/usr/bin/env bash
# §11 row 12 pre-check on localhost (no LLM): Mokli UI + Agent API + pipe SHOW_DIAGNOSTICS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI="${MOKLI_UI_URL:-http://127.0.0.1:8080}"
API="${MOKLI_AGENT_API:-http://127.0.0.1:8766/api/v2}"
PIPE="${MOKLI_PIPE_PATH:-$ROOT/deploy/mokliui/functions/mokli_pipe.py}"

curl -sf -o /dev/null -w "ui_http=%{http_code}\n" "${UI}/"
curl -sf "$API/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print('agent_api_ok', d.get('ok'))"

if [[ -f "$PIPE" ]]; then
  if grep -q SHOW_DIAGNOSTICS "$PIPE"; then
    echo "pipe_show_diagnostics=present"
  else
    echo "pipe_show_diagnostics=missing" >&2
    exit 1
  fi
else
  echo "WARN: pipe not found at $PIPE (set MOKLI_PIPE_PATH on VPS checkout)" >&2
fi

cat <<'NOTE'

§11 row 12 (desktop) — after quota probe passes:
  1. Enable Mokli pipe SHOW_DIAGNOSTICS (and SHOW_TIMELINE if desired).
  2. Chat via UI pipe (not raw Agent API); save JSONL as section11-events/12-desktop-ui.jsonl.
  3. Screenshot activity line + Arabic decision card.
  4. bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13

NOTE
