#!/usr/bin/env bash
# Shared stderr hints when §11 LLM quota probe fails (sourced, not executed).

# Parse mokli_upgrade_diagnostic_extract.py one-line summary (avoid matching nested_in=0).
section11_parse_probe_in() {
  local summary="${1:-}" tok
  for tok in $summary; do
    if [[ "$tok" == in=* ]]; then
      echo "${tok#in=}"
      return 0
    fi
  done
}

section11_jsonl_indicates_quota_block() {
  local file="${1:-}"
  [[ -n "$file" && -f "$file" ]] || return 1
  grep -qE \
    'Rate limit exceeded|free-models-per-day|"error_kind"[[:space:]]*:[[:space:]]*"rate_limit"' \
    "$file" 2>/dev/null
}

# Drop prior quota-failed row output so pick_row_diagnostic does not keep stale in=0 v2 files.
# Drop legacy 05-subagents.jsonl when spawn hit upstream 429 but parent turn kept in>0 (nested=0).
section11_prune_row5_stale_no_nested() {
  local event_dir="$1"
  local install="${2:-}"
  local stale="$event_dir/05-subagents.jsonl"
  [[ -f "$stale" ]] || return 0
  if ! grep -qE '429|rate-limited upstream|Rate limit exceeded' "$stale" 2>/dev/null; then
    return 0
  fi
  if ! grep -q spawn "$stale" 2>/dev/null; then
    return 0
  fi
  local py="${install}/.venv/bin/python"
  [[ -x "$py" ]] || py=python3
  local extract="${install}/scripts/mokli_upgrade_diagnostic_extract.py"
  [[ -f "$extract" ]] || return 0
  local line nested_val
  line=$("$py" "$extract" --file "$stale" 2>/dev/null || true)
  nested_val=$(echo "$line" | sed -n 's/.* nested_rounds=\([0-9][0-9]*\).*/\1/p' | head -1)
  nested_val=${nested_val:-0}
  if [[ "$nested_val" -eq 0 ]]; then
    echo "WARN: removing stale 05-subagents.jsonl (spawn upstream 429, nested_rounds=0)" >&2
    rm -f "$stale"
  fi
}

section11_prune_quota_failed_output() {
  local event_dir="$1"
  local out_name="$2"
  local install="${3:-}"
  case "$out_name" in
    quota-probe.jsonl | quota-probe*.jsonl | quota-before-* | probe-* | q-*.jsonl | on-vps-local-probe.jsonl)
      return 0
      ;;
  esac
  local path="$event_dir/$out_name"
  [[ -f "$path" ]] || return 0
  local py="${install}/.venv/bin/python"
  [[ -x "$py" ]] || py=python3
  local extract="${install}/scripts/mokli_upgrade_diagnostic_extract.py"
  [[ -f "$extract" ]] || extract=""
  local line="" in_val=""
  if [[ -n "$extract" ]]; then
    line=$("$py" "$extract" --file "$path" 2>/dev/null || true)
    in_val=$(section11_parse_probe_in "$line")
  fi
  if section11_jsonl_indicates_quota_block "$path" \
    || { [[ -n "$in_val" ]] && [[ "$in_val" -eq 0 ]]; }; then
    echo "WARN: removing quota-failed ${out_name} before live turn" >&2
    rm -f "$path"
  fi
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

# Cloud Agent vs VPS git tip (SSH optional). Args: repo_root [vps_branch]
section11_print_cloud_vps_rev() {
  local root="${1:?}"
  local branch="${2:-cursor/section11-vps-rows-d9e1}"
  local cloud_rev vps_rev
  local install="${MOKLI_INSTALL_DIR:-/opt/nanoagent}"
  local user="${MOKLI_SERVICE_USER:-nanoagent}"
  cloud_rev=$(git -C "$root" rev-parse --short=7 HEAD 2>/dev/null || echo unknown)
  echo "cloud_agent_rev=$cloud_rev"
  # shellcheck source=scripts/vps_ssh.sh
  source "$root/scripts/vps_ssh.sh"
  if vps_ssh_ready; then
    vps_rev=$(
      vps_ssh "sudo -u ${user} git -C ${install} rev-parse --short=7 HEAD" 2>/dev/null || true
    )
    vps_rev=${vps_rev:-unknown}
    echo "vps_rev=$vps_rev"
    if [[ "$vps_rev" != unknown && "$cloud_rev" != unknown && "$vps_rev" != "$cloud_rev" ]]; then
      echo "HINT: VPS rev != Cloud Agent — bash scripts/vps_pull_main.sh ${branch}" >&2
    fi
  else
    echo "vps_rev=skipped (no SSH)"
  fi
}

# Markdown preview gate: validate --allow-partial closure_errors (validate exits non-zero).
# Args: python validate_py events_dir results_json require_through
section11_allow_partial_closure_errors() {
  local py="${1:?}" validate_py="${2:?}" events="${3:?}" results="${4:?}"
  local require="${5:-13}"
  if [[ "$require" -lt 13 ]]; then
    return 0
  fi
  [[ -d "$events" && -f "$results" ]] || return 0
  set +e
  "$py" "$validate_py" \
    --dir "$events" --results "$results" --require-through "$require" --allow-partial 2>&1 \
    | sed -n 's/^closure_errors=\([0-9]*\).*/\1/p' | tail -1
  set -e
}

