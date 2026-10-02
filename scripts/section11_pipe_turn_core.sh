#!/usr/bin/env bash
# Shared Mokli pipe §11 turn (localhost). Sourced by vps_section11_pipe_turn.sh.

section11_run_pipe_turn() {
  local INSTALL="$1"
  local OUT_NAME="$2"
  local PROMPT="$3"
  local SERVICE_USER="${MOKLI_SERVICE_USER:-nanoagent}"
  local PY="$INSTALL/.venv/bin/python"
  local CORE="$INSTALL/scripts/section11_pipe_turn_core.py"

  if [[ ! -x "$PY" ]]; then
    PY=python3
  fi
  if [[ ! -f "$CORE" ]]; then
    CORE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/section11_pipe_turn_core.py"
  fi

  if [[ "$(id -un)" != "$SERVICE_USER" ]] && id "$SERVICE_USER" &>/dev/null; then
    local prompt_b64
    prompt_b64=$(printf '%s' "$PROMPT" | base64 -w0 2>/dev/null || printf '%s' "$PROMPT" | base64)
    sudo -u "$SERVICE_USER" env \
      MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" \
      MOKLI_SERVICE_USER="$SERVICE_USER" \
      "$PY" "$CORE" "$INSTALL" "$OUT_NAME" "$(printf '%s' "$prompt_b64" | base64 -d)"
    return $?
  fi

  local EVENT_DIR="$INSTALL/section11-events"
  mkdir -p "$EVENT_DIR"
  if [[ -f "$INSTALL/scripts/section11_quota_hints.sh" ]]; then
    # shellcheck source=scripts/section11_quota_hints.sh
    source "$INSTALL/scripts/section11_quota_hints.sh"
    section11_prune_quota_failed_output "$EVENT_DIR" "$OUT_NAME" "$INSTALL"
  fi

  MOKLI_SECTION11_MODEL="${MOKLI_SECTION11_MODEL:-}" \
    "$PY" "$CORE" "$INSTALL" "$OUT_NAME" "$PROMPT"
}
