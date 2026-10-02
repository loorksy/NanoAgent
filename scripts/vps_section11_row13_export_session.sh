#!/usr/bin/env bash
# §11 row 13: export gateway JSONL after a live mobile/SDK chat (operator runs on VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"
# shellcheck source=scripts/section11_export_session_jsonl.sh
source "$ROOT/scripts/section11_export_session_jsonl.sh"

export MOKLI_SSH_HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
OUT="${1:-13-mobile.jsonl}"
SESSION_ID="${2:-}"

run_export() {
  local INSTALL="$1"
  local OUT_NAME="$2"
  local SID="$3"
  local TOKEN BASE

  TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
  BASE=http://127.0.0.1:8766/api/v2

  if [[ -z "$SID" ]]; then
    SID=$(curl -sf "$BASE/sessions" -H "Authorization: Bearer $TOKEN" | python3 -c "
import json, sys
body = json.load(sys.stdin)
rows = body.get('sessions') or []
if not rows:
    raise SystemExit('no sessions')
rows.sort(key=lambda r: int(r.get('updated_at') or 0), reverse=True)
print(rows[0]['id'])
")
  fi

  section11_export_session_jsonl "$INSTALL" "$SID" "$OUT_NAME"
  local path="$INSTALL/section11-events/$OUT_NAME"
  if ! section11_row13_jsonl_ok "$path"; then
    echo "ERROR row 13 JSONL missing tool/status/structured events — use mobile chat session id explicitly" >&2
    echo "HINT: bash scripts/vps_section11_row13_export_session.sh $OUT_NAME <session-id>" >&2
    return 1
  fi
}

if section11_local_ready "$INSTALL_DIR"; then
  run_export "$INSTALL_DIR" "$OUT" "$SESSION_ID"
  exit 0
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh env MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" bash -s -- "$INSTALL_DIR" "$OUT" "$SESSION_ID" <<'EOS'
set -euo pipefail
INSTALL="$1"
OUT_NAME="$2"
SID="$3"
# shellcheck source=scripts/section11_export_session_jsonl.sh
source "$INSTALL/scripts/section11_export_session_jsonl.sh"
TOKEN=$(cat "$INSTALL/.mokli/workspace/agent_api/admin_token")
BASE=http://127.0.0.1:8766/api/v2
if [[ -z "$SID" ]]; then
  SID=$(curl -sf "$BASE/sessions" -H "Authorization: Bearer $TOKEN" | python3 -c "
import json, sys
body = json.load(sys.stdin)
rows = body.get('sessions') or []
if not rows:
    raise SystemExit('no sessions')
rows.sort(key=lambda r: int(r.get('updated_at') or 0), reverse=True)
print(rows[0]['id'])
")
fi
section11_export_session_jsonl "$INSTALL" "$SID" "$OUT_NAME"
path="$INSTALL/section11-events/$OUT_NAME"
if ! section11_row13_jsonl_ok "$path"; then
  echo "ERROR row 13 JSONL missing tool/status/structured events" >&2
  exit 1
fi
EOS
