#!/usr/bin/env bash
# Export a completed Agent API session SSE log to §11 JSONL (one gateway event per line).

section11_export_session_jsonl() {
  local INSTALL="$1"
  local SESSION_ID="$2"
  local OUT_NAME="$3"
  local SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
  local TOKEN BASE EVENT_DIR RAW

  TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
  BASE=http://127.0.0.1:8766/api/v2
  EVENT_DIR="$INSTALL/section11-events"
  mkdir -p "$EVENT_DIR"
  RAW="$EVENT_DIR/raw-export-${OUT_NAME}.sse"

  if ! curl -sfN --max-time 300 "$BASE/sessions/$SESSION_ID/events?until_end=1" \
    -H "Authorization: Bearer $TOKEN" -o "$RAW"; then
    echo "section11 export: failed to read events for session $SESSION_ID" >&2
    return 1
  fi
  if ! grep -q '^data: ' "$RAW" 2>/dev/null; then
    echo "section11 export: no SSE data for session $SESSION_ID" >&2
    return 1
  fi
  grep '^data: ' "$RAW" | sed 's/^data: //' > "$EVENT_DIR/$OUT_NAME"
  echo "OK exported session $SESSION_ID → $EVENT_DIR/$OUT_NAME ($(wc -l < "$EVENT_DIR/$OUT_NAME") lines)"
  if [[ "$(id -un)" == "$SERVICE_USER" ]] && [[ -f "$INSTALL/.venv/bin/python" ]]; then
    "$INSTALL/.venv/bin/python" "$INSTALL/scripts/mokli_upgrade_diagnostic_extract.py" \
      --file "$EVENT_DIR/$OUT_NAME" 2>/dev/null || true
  fi
}

section11_row13_jsonl_ok() {
  local FILE="$1"
  [[ -f "$FILE" ]] || return 1
  grep -qE '"kind": "(tool|status|structured)"|"kind":"(tool|status|structured)"' "$FILE"
}
