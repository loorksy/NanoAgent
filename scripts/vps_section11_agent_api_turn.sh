#!/usr/bin/env bash
# Run one Agent API turn on VPS and write JSONL + diagnostic line (operator §11 helper).
# Requires: MOKLI_SSH_HOST or VPS/VPSPASS; working LLM billing on the host.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT_NAME="${1:-01-no-tools.jsonl}"
PROMPT="${2:-مرحبا، ما اسمك؟}"

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" "$OUT_NAME" "$PROMPT" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
PROMPT="$3"
TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
BASE=http://127.0.0.1:8766/api/v2
EVENT_DIR="$INSTALL/section11-events"
mkdir -p "$EVENT_DIR"
SID=$(curl -sf -X POST "$BASE/sessions" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "{\"title\":\"section11-${OUT_NAME}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
RAW="$EVENT_DIR/raw-${OUT_NAME}.sse"
curl -sfN "$BASE/sessions/$SID/events?until_end=1" -H "Authorization: Bearer $TOKEN" -o "$RAW" &
sleep 1
curl -sf -X POST "$BASE/sessions/$SID/messages" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "$(python3 -c "import json,sys; print(json.dumps({'text':sys.argv[1]}))" "$PROMPT")"
wait
grep '^data: ' "$RAW" | sed 's/^data: //' > "$EVENT_DIR/$OUT_NAME"
sudo -u nanoagent bash -lc "cd '$INSTALL' && source .venv/bin/activate && \
  python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT_NAME"
EOS
