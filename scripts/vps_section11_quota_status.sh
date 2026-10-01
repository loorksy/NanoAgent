#!/usr/bin/env bash
# Report last §11 quota-probe JSONL without a new Agent API turn (default: fresh within 6h).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
export MOKLI_SSH_HOST="$HOST"
MAX_AGE_MIN="${MOKLI_QUOTA_STATUS_MAX_AGE_MIN:-360}"
REQUIRE_FRESH=0

usage() {
  echo "Usage: $0 [--require-fresh]" >&2
  echo "  Reads section11-events/quota-probe.jsonl (or newest quota-*.jsonl) on VPS/install." >&2
  echo "  Exit 0 when last diagnostic in>0 and age <= ${MAX_AGE_MIN}m." >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require-fresh) REQUIRE_FRESH=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown arg: $1" >&2; usage ;;
  esac
done

_run_status() {
  local install="$1"
  local user="$2"
  local events="$install/section11-events"
  local probe=""
  if [[ -f "$events/quota-probe.jsonl" ]]; then
    probe="$events/quota-probe.jsonl"
  else
    probe=$(ls -t "$events"/quota-*.jsonl 2>/dev/null | head -1 || true)
  fi
  if [[ -z "${probe:-}" || ! -f "$probe" ]]; then
    echo "MISSING no quota-probe JSONL under $events"
    return 3
  fi
  local age_min=$(( ($(date +%s) - $(stat -c %Y "$probe")) / 60 ))
  if [[ "$REQUIRE_FRESH" -eq 1 && "$age_min" -gt "$MAX_AGE_MIN" ]]; then
    echo "STALE probe=$(basename "$probe") age_min=$age_min max=$MAX_AGE_MIN"
    return 4
  fi
  local rel="section11-events/$(basename "$probe")"
  local line
  if [[ "$(id -un)" == "$user" ]]; then
    line=$(bash -lc "cd '$install' && source .venv/bin/activate && \
      python scripts/mokli_upgrade_diagnostic_extract.py --file '$rel'" 2>/dev/null || true)
  else
    line=$(sudo -u "$user" bash -lc "cd '$install' && source .venv/bin/activate && \
      python scripts/mokli_upgrade_diagnostic_extract.py --file '$rel'" 2>/dev/null || true)
  fi
  if [[ -z "${line:-}" ]]; then
    echo "INVALID probe=$(basename "$probe") (no diagnostic)"
    return 5
  fi
  echo "probe=$(basename "$probe") age_min=$age_min $line"
  if grep -q 'Rate limit exceeded\|free-models-per-day' "$probe" 2>/dev/null \
    || echo "$line" | grep -qE '(^| )in=0([^0-9]|$)'; then
    echo "QUOTA_BLOCKED: cached (run vps_section11_quota_probe.sh after credits)"
    return 1
  fi
  echo "QUOTA_OK cached"
  return 0
}

if section11_local_ready "$INSTALL_DIR"; then
  _run_status "$INSTALL_DIR" "$SERVICE_USER"
  exit $?
fi

if ! vps_ssh_ready; then
  bash "$ROOT/scripts/cloud_agent_vps_secrets_check.sh" >&2 || true
  exit 1
fi

vps_ssh bash -s -- "$INSTALL_DIR" "$SERVICE_USER" "$MAX_AGE_MIN" "$REQUIRE_FRESH" <<'EOS'
set -uo pipefail
install="$1"
user="$2"
MAX_AGE_MIN="$3"
REQUIRE_FRESH="$4"
events="$install/section11-events"
probe=""
if [[ -f "$events/quota-probe.jsonl" ]]; then
  probe="$events/quota-probe.jsonl"
else
  probe=$(ls -t "$events"/quota-*.jsonl 2>/dev/null | head -1 || true)
fi
if [[ -z "${probe:-}" || ! -f "$probe" ]]; then
  echo "MISSING no quota-probe JSONL"
  exit 3
fi
age_min=$(( ($(date +%s) - $(stat -c %Y "$probe")) / 60 ))
if [[ "$REQUIRE_FRESH" == 1 && "$age_min" -gt "$MAX_AGE_MIN" ]]; then
  echo "STALE probe=$(basename "$probe") age_min=$age_min max=$MAX_AGE_MIN"
  exit 4
fi
rel="section11-events/$(basename "$probe")"
line=$(sudo -u "$user" bash -lc "cd '$install' && source .venv/bin/activate && \
  python scripts/mokli_upgrade_diagnostic_extract.py --file '$rel'" 2>/dev/null || true)
if [[ -z "${line:-}" ]]; then
  echo "INVALID probe=$(basename "$probe")"
  exit 5
fi
echo "probe=$(basename "$probe") age_min=$age_min $line"
if grep -q 'Rate limit exceeded\|free-models-per-day' "$probe" 2>/dev/null \
  || echo "$line" | grep -qE '(^| )in=0([^0-9]|$)'; then
  echo "QUOTA_BLOCKED: cached (run vps_section11_quota_probe.sh after credits)"
  exit 1
fi
echo "QUOTA_OK cached"
exit 0
EOS
