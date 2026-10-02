#!/usr/bin/env bash
# Shared stderr hints when §11 LLM quota probe fails (sourced, not executed).

# Parse mokli_upgrade_diagnostic_extract.py one-line summary (avoid matching nested_in=0).
section11_parse_probe_in() {
  local summary="${1:-}"
  local val
  val=$(echo "$summary" | sed -n 's/.* rounds=1 in=\([0-9][0-9]*\).*/\1/p' | head -1)
  if [[ -n "$val" ]]; then
    echo "$val"
    return 0
  fi
  val=$(echo "$summary" | sed -n 's/.* in=\([0-9][0-9]*\).*/\1/p' | head -1)
  [[ -n "$val" ]] && echo "$val"
}

section11_jsonl_indicates_quota_block() {
  local file="${1:-}"
  [[ -n "$file" && -f "$file" ]] || return 1
  grep -qE \
    'Rate limit exceeded|free-models-per-day|"error_kind"[[:space:]]*:[[:space:]]*"rate_limit"' \
    "$file" 2>/dev/null
}

section11_print_quota_unblock_hints() {
  echo "HINT: OpenRouter credits or export MOKLI_SECTION11_MODEL=… on this shell (forwarded over SSH; docs/section11-vps-env.example)" >&2
  echo "HINT: free-models-per-day / 429 — pause §11 rows 9–13 until quota returns; rerun vps_section11_quota_probe.sh" >&2
  echo "HINT: while blocked, reset clock without LLM — bash scripts/vps_section11_quota_status.sh --local-dir section11-events" >&2
  if [[ -n "${MOKLI_SECTION11_MODEL:-}" ]]; then
    echo "HINT: MOKLI_SECTION11_MODEL is set but probe still failed — verify model id / provider billing" >&2
  fi
}

# From mokli_upgrade_section11_wait_quota_reset.sh stdout (seconds_until_reset=… buffer_sec=…).
section11_emit_wake_after_buffer() {
  local reset_out="${1:-}"
  local reset_secs buffer_secs wake_after eta
  reset_secs=$(printf '%s\n' "$reset_out" | sed -n 's/^seconds_until_reset=\([0-9]*\).*/\1/p' | tail -1)
  buffer_secs=$(printf '%s\n' "$reset_out" | sed -n 's/^seconds_until_reset=[0-9]* buffer_sec=\([0-9]*\).*/\1/p' | tail -1)
  if [[ -z "$reset_secs" || ! "$reset_secs" =~ ^[0-9]+$ ]]; then
    return 0
  fi
  buffer_secs=${buffer_secs:-120}
  wake_after=$(( reset_secs + buffer_secs ))
  echo "wake_after_buffer_sec=${wake_after}"
  if eta=$(date -u -d "@$(($(date +%s) + wake_after))" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null); then
    echo "wake_after_buffer_utc=${eta}"
  fi
}

