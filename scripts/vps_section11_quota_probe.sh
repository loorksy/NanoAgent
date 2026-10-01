#!/usr/bin/env bash
# Quick VPS LLM probe for §11 (no patch): one Agent API turn; exit 1 if quota/rate-limit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/vps_ssh.sh
source "$ROOT/scripts/vps_ssh.sh"
# shellcheck source=scripts/section11_quota_hints.sh
source "$ROOT/scripts/section11_quota_hints.sh"
# shellcheck source=scripts/section11_agent_api_turn_core.sh
source "$ROOT/scripts/section11_agent_api_turn_core.sh"

OUT="${1:-quota-probe.jsonl}"
HOST="${MOKLI_SSH_HOST:-hostinger-vps}"
export MOKLI_SSH_HOST="$HOST"
INSTALL_DIR="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3

section11_quota_reset_hint() {
  local jsonl="$1"
  [[ -f "$jsonl" ]] || return 0
  "$PYTHON" "$ROOT/scripts/section11_quota_reset_hint.py" "$jsonl" >&2 || true
}

section11_pull_probe_to_workspace() {
  local out="$1"
  if section11_local_ready "$INSTALL_DIR"; then
    return 0
  fi
  local local_dir="${ROOT}/section11-events"
  mkdir -p "$local_dir"
  local dest="${local_dir}/${out}"
  local bak="${dest}.bak"
  if [[ -f "$dest" ]]; then
    cp "$dest" "$bak"
  fi
  if ! scp -o BatchMode=yes "${HOST}:${INSTALL_DIR}/section11-events/${out}" "${local_dir}/" 2>/dev/null; then
    if [[ -f "$bak" ]]; then
      mv "$bak" "$dest"
    fi
    return 1
  fi
  echo "OK cached probe → ${dest}" >&2
  if [[ ! -f "$dest" ]]; then
    return 1
  fi
  if [[ -f "$bak" ]]; then
    restore=$("$PYTHON" "$ROOT/scripts/section11_probe_cache_preserve.py" "$dest" "$bak" 2>/dev/null || echo no)
    if [[ "$restore" == "yes" ]]; then
      echo "WARN: incomplete probe pulled — keeping previous ${out}" >&2
      mv "$bak" "$dest"
      return 0
    fi
  fi
  rm -f "$bak"
}

run_probe_checks() {
  local jsonl="$1"
  if section11_jsonl_indicates_quota_block "$jsonl"; then
    echo "QUOTA_BLOCKED: OpenRouter free daily limit or 429 in $OUT" >&2
    section11_print_quota_unblock_hints
    section11_quota_reset_hint "$jsonl"
    return 1
  fi
  local extract_cmd
  if [[ "$(id -un)" == "${MOKLI_SERVICE_USER:-nanoagent}" ]]; then
    extract_cmd="cd '$INSTALL_DIR' && source .venv/bin/activate && python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT"
  else
    extract_cmd="sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc \"cd '$INSTALL_DIR' && source .venv/bin/activate && python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT\""
  fi
  local line
  line=$(bash -lc "$extract_cmd" 2>/dev/null || true)
  echo "$line"
  local in_val
  in_val=$(echo "$line" | sed -n 's/.*in=\([0-9]*\).*/\1/p' | head -1)
  if [[ -z "${in_val:-}" || "$in_val" == "0" ]]; then
    if ! grep -q '"kind": "diagnostic"' "$jsonl" 2>/dev/null; then
      echo "QUOTA_BLOCKED: no diagnostic in $OUT (incomplete turn; rate limit likely)" >&2
    else
      echo "QUOTA_BLOCKED: diagnostic input_tokens=0 in $OUT" >&2
    fi
    section11_print_quota_unblock_hints
    section11_quota_reset_hint "$jsonl"
    return 1
  fi
  echo "QUOTA_OK in=$in_val file=$OUT"
}

if section11_local_ready "$INSTALL_DIR"; then
  bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" 'Reply with exactly: OK'
  run_probe_checks "$INSTALL_DIR/section11-events/$OUT"
  exit $?
fi

export MOKLI_SSH_HOST="$HOST"
MOKLI_SSH_HOST="$HOST" bash "$ROOT/scripts/vps_section11_agent_api_turn.sh" "$OUT" 'Reply with exactly: OK'
section11_pull_probe_to_workspace "$OUT"

if ssh -o BatchMode=yes "$HOST" \
  "grep -qE 'Rate limit exceeded|free-models-per-day|\"error_kind\"[[:space:]]*:[[:space:]]*\"rate_limit\"' \
    ${INSTALL_DIR}/section11-events/$OUT 2>/dev/null"; then
  echo "QUOTA_BLOCKED: OpenRouter free daily limit or 429 in $OUT" >&2
  section11_print_quota_unblock_hints
  ssh -o BatchMode=yes "$HOST" \
    "sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc 'cd $(printf '%q' "$INSTALL_DIR") && \
      python3 scripts/section11_quota_reset_hint.py section11-events/$OUT'" >&2 || true
  exit 1
fi

extract_out=$(ssh -o BatchMode=yes "$HOST" \
  "sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc 'cd ${INSTALL_DIR} && source .venv/bin/activate && \
    python scripts/mokli_upgrade_diagnostic_extract.py --file section11-events/$OUT'" 2>&1) || true
IN=$(echo "$extract_out" | sed -n 's/.*in=\([0-9]*\).*/\1/p' | head -1)

if [[ -z "${IN:-}" || "$IN" == "0" ]]; then
  if echo "$extract_out" | grep -qi 'no diagnostic'; then
    echo "QUOTA_BLOCKED: no diagnostic in $OUT (incomplete turn; rate limit likely)" >&2
  else
    echo "QUOTA_BLOCKED: diagnostic input_tokens=0 in $OUT" >&2
  fi
  section11_print_quota_unblock_hints
  ssh -o BatchMode=yes "$HOST" \
    "sudo -u ${MOKLI_SERVICE_USER:-nanoagent} bash -lc 'cd $(printf '%q' "$INSTALL_DIR") && \
      python3 scripts/section11_quota_reset_hint.py section11-events/$OUT'" >&2 || true
  exit 1
fi

echo "QUOTA_OK in=$IN file=$OUT"
