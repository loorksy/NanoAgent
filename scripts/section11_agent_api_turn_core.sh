#!/usr/bin/env bash
# Shared Agent API §11 turn (localhost). Sourced by vps_section11_agent_api_turn.sh.

section11_local_ready() {
  local install="${1:-${MOKLI_INSTALL_DIR:-/opt/nanoagent}}"
  [[ -f "${install}/.mokli/workspace/agent_api/admin_token" ]] \
    && curl -sf http://127.0.0.1:8766/api/v2/health >/dev/null 2>&1
}

section11_run_agent_api_turn() {
  local INSTALL="$1"
  local OUT_NAME="$2"
  local PROMPT="$3"
  local SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"

  local TOKEN BASE EVENT_DIR SID RAW SSE_PID
  TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
  BASE=http://127.0.0.1:8766/api/v2
  EVENT_DIR="$INSTALL/section11-events"
  mkdir -p "$EVENT_DIR"
  SID=$(curl -sf -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d "{\"title\":\"section11-${OUT_NAME}\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  RAW="$EVENT_DIR/raw-${OUT_NAME}.sse"
  curl -sfN --max-time 900 "$BASE/sessions/$SID/events?until_end=1" \
    -H "Authorization: Bearer $TOKEN" -o "$RAW" &
  SSE_PID=$!
  sleep 1
  MSG_BODY=$(PROMPT="$PROMPT" MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" python3 -c "
import json, os
body = {'text': os.environ['PROMPT']}
model = os.environ.get('MOKLI_SECTION11_MODEL', '').strip()
if model:
    body['model'] = model
print(json.dumps(body))
")
  POST_OUT=$(curl -sS -w "\n%{http_code}" -X POST "$BASE/sessions/$SID/messages" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$MSG_BODY")
  POST_CODE=$(printf '%s' "$POST_OUT" | tail -n1)
  POST_BODY=$(printf '%s' "$POST_OUT" | sed '$d')
  if [[ "$POST_CODE" != "202" && "$POST_CODE" != "200" ]]; then
    echo "section11: message POST failed http=$POST_CODE body=$POST_BODY" >&2
    kill "$SSE_PID" 2>/dev/null || true
    wait "$SSE_PID" 2>/dev/null || true
    exit 1
  fi
  for _ in $(seq 1 90); do
    grep '^data: ' "$RAW" 2>/dev/null | sed 's/^data: //' > "$EVENT_DIR/$OUT_NAME" || true
    if grep -q '"kind": "diagnostic"' "$EVENT_DIR/$OUT_NAME" 2>/dev/null \
      || grep -q '"kind":"diagnostic"' "$EVENT_DIR/$OUT_NAME" 2>/dev/null; then
      break
    fi
    if curl -sf "$BASE/sessions/$SID" -H "Authorization: Bearer $TOKEN" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); sd=d.get('state_detail') or d; print(sd.get('state'), sd.get('run'))" \
      | grep -qE '^completed( |$)'; then
      if grep -q '^data: ' "$RAW" 2>/dev/null; then
        break
      fi
    fi
    sleep 2
  done
  kill "$SSE_PID" 2>/dev/null || true
  wait "$SSE_PID" 2>/dev/null || true
  grep '^data: ' "$RAW" | sed 's/^data: //' > "$EVENT_DIR/$OUT_NAME"
  if [[ "$(id -un)" == "$SERVICE_USER" ]]; then
    bash -lc "cd '$INSTALL' && source .venv/bin/activate && \
      python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT_NAME"
  else
    sudo -u "$SERVICE_USER" bash -lc "cd '$INSTALL' && source .venv/bin/activate && \
      python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT_NAME"
  fi
}
