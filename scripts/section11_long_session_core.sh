#!/usr/bin/env bash
# §11 row 9: multi-round session on localhost Agent API. Sourced by vps_section11_long_session.sh.

section11_run_long_session() {
  local INSTALL="$1"
  local OUT_NAME="$2"
  local ROUNDS="$3"
  local PROMPT="$4"
  local SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"

  if [[ "$(id -un)" != "$SERVICE_USER" ]] && id "$SERVICE_USER" &>/dev/null; then
    local prompt_b64
    prompt_b64=$(printf '%s' "$PROMPT" | base64 -w0 2>/dev/null || printf '%s' "$PROMPT" | base64)
    sudo -u "$SERVICE_USER" env MOKLI_SERVICE_USER="$SERVICE_USER" \
      bash -s -- "$INSTALL" "$OUT_NAME" "$ROUNDS" "$prompt_b64" <<'SECTION11_LONG_AS_USER'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
ROUNDS="$3"
PROMPT=$(printf '%s' "$4" | base64 -d)
# shellcheck source=/dev/null
source "$INSTALL/scripts/section11_long_session_core.sh"
section11_run_long_session "$INSTALL" "$OUT_NAME" "$ROUNDS" "$PROMPT"
SECTION11_LONG_AS_USER
    return $?
  fi

  local TOKEN BASE EVENT_DIR OUT SID
  TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
  BASE=http://127.0.0.1:8766/api/v2
  EVENT_DIR="$INSTALL/section11-events"
  mkdir -p "$EVENT_DIR"
  OUT="$EVENT_DIR/$OUT_NAME"
  : > "$OUT"
  SID=$(curl -sf -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d "{\"title\":\"section11-long\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

  wait_session_idle() {
    for _ in $(seq 1 180); do
      if curl -sf "$BASE/sessions/$SID" -H "Authorization: Bearer $TOKEN" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); sd=d.get('state_detail') or d; print('busy' if sd.get('state')=='working' else 'idle')" \
        | grep -q '^idle$'; then
        return 0
      fi
      sleep 2
    done
    echo "section11: session still busy after wait" >&2
    return 1
  }

  local n RAW SSE_PID
  for n in $(seq 1 "$ROUNDS"); do
    wait_session_idle || true
    RAW="$EVENT_DIR/raw-${OUT_NAME%.jsonl}-${n}.sse"
    : > "$RAW"
    curl -sfN --max-time 600 "$BASE/sessions/$SID/events?until_end=1" \
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
      echo "section11: round $n message POST failed http=$POST_CODE body=$POST_BODY" >&2
      kill "$SSE_PID" 2>/dev/null || true
      wait "$SSE_PID" 2>/dev/null || true
      sleep 5
      continue
    fi
    for _ in $(seq 1 90); do
      if grep -q '^data: ' "$RAW" 2>/dev/null && \
        grep '^data: ' "$RAW" | sed 's/^data: //' | grep -q '"kind".*"diagnostic"'; then
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
    grep '^data: ' "$RAW" | sed 's/^data: //' >> "$OUT"
    echo "{\"kind\":\"section11_round_marker\",\"data\":{\"round\":$n}}" >> "$OUT"
    wait_session_idle || true
  done

  local extract="cd '$INSTALL' && source .venv/bin/activate && python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT_NAME --session-summary"
  if [[ "$(id -un)" == "$SERVICE_USER" ]]; then
    bash -lc "$extract"
  else
    sudo -u "$SERVICE_USER" bash -lc "$extract"
  fi
}
