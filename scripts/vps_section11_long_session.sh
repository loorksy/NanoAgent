#!/usr/bin/env bash
# §11 row 9: many tool rounds in one Agent API session; append SSE to one JSONL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT_NAME="${1:-09-long-session.jsonl}"
ROUNDS="${2:-15}"
PROMPT="${3:-Call get_gold_quote once only. Reply with OK.}"

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

PROMPT_B64=$(printf '%s' "$PROMPT" | base64 -w0)

vps_ssh bash -s -- "$INSTALL_DIR" "$OUT_NAME" "$ROUNDS" "$PROMPT_B64" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
ROUNDS="$3"
PROMPT=$(printf '%s' "$4" | base64 -d)
TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
BASE=http://127.0.0.1:8766/api/v2
EVENT_DIR="$INSTALL/section11-events"
mkdir -p "$EVENT_DIR"
OUT="$EVENT_DIR/$OUT_NAME"
: > "$OUT"
SID=$(curl -sf -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "{\"title\":\"section11-long\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
for n in $(seq 1 "$ROUNDS"); do
  RAW="$EVENT_DIR/raw-${OUT_NAME%.jsonl}-${n}.sse"
  curl -sfN --max-time 600 "$BASE/sessions/$SID/events?until_end=1" \
    -H "Authorization: Bearer $TOKEN" -o "$RAW" &
  SSE_PID=$!
  sleep 1
  curl -sf -X POST "$BASE/sessions/$SID/messages" -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$(PROMPT="$PROMPT" python3 -c "import json,os; print(json.dumps({'text':os.environ['PROMPT']}))")"
  wait "$SSE_PID" || true
  for _ in $(seq 1 45); do
    if grep -q '^data: ' "$RAW" 2>/dev/null && \
      grep '^data: ' "$RAW" | sed 's/^data: //' | grep -q '"kind".*"diagnostic"'; then
      break
    fi
    sleep 2
  done
  grep '^data: ' "$RAW" | sed 's/^data: //' >> "$OUT"
  echo "{\"kind\":\"section11_round_marker\",\"data\":{\"round\":$n}}" >> "$OUT"
  sleep 1
done
sudo -u nanoagent bash -lc "cd '$INSTALL' && source .venv/bin/activate && \
  python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT_NAME"
EOS
