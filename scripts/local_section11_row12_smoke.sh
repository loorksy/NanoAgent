#!/usr/bin/env bash
# §11 row 12 pre-check on localhost (no LLM): Mokli UI + Agent API + pipe SHOW_DIAGNOSTICS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API="${MOKLI_AGENT_API:-http://127.0.0.1:8766/api/v2}"
PIPE="${MOKLI_PIPE_PATH:-$ROOT/deploy/mokliui/functions/mokli_pipe.py}"

resolve_ui_url() {
  if [[ -n "${MOKLI_UI_URL:-}" ]]; then
    echo "$MOKLI_UI_URL"
    return
  fi
  local base
  for base in "http://127.0.0.1:5173" "http://127.0.0.1:8080"; do
    if curl -sf --max-time 5 -o /dev/null "${base}/" 2>/dev/null \
      || curl -sf --max-time 5 -o /dev/null "${base}/api/v2/health" 2>/dev/null; then
      echo "$base"
      return
    fi
  done
  echo "http://127.0.0.1:5173"
}

UI="$(resolve_ui_url)"
ui_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 8 "${UI}/" 2>/dev/null \
  || curl -sf -o /dev/null -w "%{http_code}" --max-time 8 "${UI}/api/v2/health" 2>/dev/null \
  || echo "000")
echo "ui_url=${UI} ui_http=${ui_code}"
if [[ "$ui_code" == "000" ]]; then
  echo "HINT: start Mokli UI — cd mokli-ui && bun run dev --host 127.0.0.1 --port 5173" >&2
  echo "HINT: or set MOKLI_UI_URL (VPS Mokli often http://127.0.0.1:8080)" >&2
  exit 1
fi
curl -sf --max-time 8 "$API/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print('agent_api_ok', d.get('ok'))"

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
  4. bash scripts/mokli_upgrade_section11_close.sh --apply --require-through 13 --results section11-results-partial.json

NOTE
