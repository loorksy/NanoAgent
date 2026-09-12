#!/usr/bin/env bash
# Sync OANDA credentials from the production foxagent VPS into a local .env file.
# Requires Cloud Agent secrets VPS (host) and VPSPASS, or manual SSH access.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
MARKER="# --- OANDA (synced from foxagent VPS) ---"

if [[ -n "${OANDA_API_TOKEN:-}" && -n "${OANDA_ACCOUNT_ID:-}" ]]; then
  exit 0
fi

if [[ -z "${VPS:-}" || -z "${VPSPASS:-}" ]]; then
  echo "sync-oanda: VPS/VPSPASS not set; skipping OANDA sync" >&2
  exit 0
fi

command -v sshpass >/dev/null 2>&1 || {
  echo "sync-oanda: sshpass required" >&2
  exit 0
}

payload="$(sshpass -p "$VPSPASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "root@${VPS}" \
  "docker exec foxagent-backend python -c \"
import sqlite3, json
from app.services.settings_store import _fernet
conn = sqlite3.connect('/data/foxagent.db')
raw = conn.execute('SELECT value FROM settings WHERE key=?', ('runtime_settings',)).fetchone()[0]
data = json.loads(_fernet().decrypt(raw.encode()).decode())
print(json.dumps({
    'token': data.get('oandaApiToken', ''),
    'account': data.get('oandaAccountId', ''),
    'env': data.get('oandaEnvironment', 'practice') or 'practice',
}))
\"" 2>/dev/null || true)"

token="$(python3 -c "import json,sys; d=json.loads(sys.argv[1] or '{}'); print(d.get('token',''))" "$payload" 2>/dev/null || true)"
account="$(python3 -c "import json,sys; d=json.loads(sys.argv[1] or '{}'); print(d.get('account',''))" "$payload" 2>/dev/null || true)"
oanda_env="$(python3 -c "import json,sys; d=json.loads(sys.argv[1] or '{}'); print(d.get('env','practice'))" "$payload" 2>/dev/null || true)"

if [[ -z "$token" || -z "$account" ]]; then
  echo "sync-oanda: no OANDA credentials found on foxagent VPS" >&2
  exit 0
fi

touch "$ENV_FILE"
python3 - "$ENV_FILE" "$MARKER" "$token" "$account" "$oanda_env" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
marker = sys.argv[2]
token, account, oanda_env = sys.argv[3], sys.argv[4], sys.argv[5]
lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
out: list[str] = []
skip = False
for line in lines:
    if line.strip() == marker:
        skip = True
        continue
    if skip:
        if line.startswith("# ---") and line.strip() != marker:
            skip = False
            out.append(line)
        continue
    out.append(line)
while out and not out[-1].strip():
    out.pop()
if out and out[-1].strip():
    out.append("")
out.extend([
    marker,
    f"OANDA_API_TOKEN={token}",
    f"OANDA_ACCOUNT_ID={account}",
    f"OANDA_ENV={oanda_env}",
    "",
])
env_path.write_text("\n".join(out), encoding="utf-8")
PY

chmod 600 "$ENV_FILE" 2>/dev/null || true
echo "sync-oanda: wrote OANDA credentials to .env"
