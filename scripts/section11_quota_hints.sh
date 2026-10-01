#!/usr/bin/env bash
# Shared stderr hints when §11 LLM quota probe fails (sourced, not executed).

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
  if [[ -n "${MOKLI_SECTION11_MODEL:-}" ]]; then
    echo "HINT: MOKLI_SECTION11_MODEL is set but probe still failed — verify model id / provider billing" >&2
  fi
}
