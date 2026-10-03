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

  # Cloud-agent SSH runs as root; JSONL must be owned by the gateway user for on-VPS reruns.
  if [[ "$(id -un)" != "$SERVICE_USER" ]] && id "$SERVICE_USER" &>/dev/null; then
    local prompt_b64
    prompt_b64=$(printf '%s' "$PROMPT" | base64 -w0 2>/dev/null || printf '%s' "$PROMPT" | base64)
    sudo -u "$SERVICE_USER" env \
      MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" \
      MOKLI_SERVICE_USER="$SERVICE_USER" \
      bash -s -- "$INSTALL" "$OUT_NAME" "$prompt_b64" <<'SECTION11_TURN_AS_USER'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
PROMPT=$(printf '%s' "$3" | base64 -d)
# shellcheck source=/dev/null
source "$INSTALL/scripts/section11_agent_api_turn_core.sh"
section11_run_agent_api_turn "$INSTALL" "$OUT_NAME" "$PROMPT"
SECTION11_TURN_AS_USER
    return $?
  fi

  local TOKEN BASE EVENT_DIR SID RAW SSE_PID
  TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
  BASE=http://127.0.0.1:8766/api/v2
  EVENT_DIR="$INSTALL/section11-events"
  mkdir -p "$EVENT_DIR"
  if [[ -f "$INSTALL/scripts/section11_quota_hints.sh" ]]; then
    # shellcheck source=scripts/section11_quota_hints.sh
    source "$INSTALL/scripts/section11_quota_hints.sh"
    section11_prune_quota_failed_output "$EVENT_DIR" "$OUT_NAME" "$INSTALL"
  fi
  SID=""
  for _try in 1 2 3; do
    _sess_body=$(curl -sf -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" -d "{\"title\":\"section11-${OUT_NAME}\"}" || true)
    if [[ -n "${_sess_body:-}" ]]; then
      SID=$(printf '%s' "$_sess_body" | python3 -c "import sys,json
raw=sys.stdin.read().strip()
if not raw:
    raise SystemExit('empty session response')
print(json.loads(raw)['id'])") || true
    fi
    if [[ -n "${SID:-}" ]]; then
      break
    fi
    sleep 2
  done
  if [[ -z "${SID:-}" ]]; then
    echo "section11: failed to create session (Agent API may be restarting — retry in a few seconds)" >&2
    exit 1
  fi
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
