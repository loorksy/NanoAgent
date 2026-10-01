#!/usr/bin/env bash
# Compare §11/P0 diagnostic input tokens: baseline JSONL vs a new live turn.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
EXTRACT="${ROOT}/scripts/mokli_upgrade_diagnostic_extract.py"

BASELINE="${1:-$ROOT/section11-events/01-no-tools.jsonl}"
NEW="${2:?Usage: $0 [baseline.jsonl] new-turn.jsonl}"

for f in "$BASELINE" "$NEW"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing file: $f" >&2
    exit 1
  fi
done

base_line="$("$PYTHON" "$EXTRACT" --file "$BASELINE")"
new_line="$("$PYTHON" "$EXTRACT" --file "$NEW" 2>/dev/null)" || new_line=""
if [[ -z "$new_line" ]]; then
  if grep -qE \
    'Rate limit exceeded|free-models-per-day|"error_kind"[[:space:]]*:[[:space:]]*"rate_limit"' \
    "$NEW" 2>/dev/null; then
    base_in=$("$PYTHON" "$EXTRACT" --file "$BASELINE" | awk '{
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^in=[0-9]+$/) { sub(/^in=/, "", $i); print $i; exit }
      }
    }')
    IFS='|' read -r base_pt base_final base_tool_defs <<< "$("$PYTHON" "$EXTRACT" --file "$BASELINE" --json | "$PYTHON" -c "
import json, sys
d = json.load(sys.stdin)
comp = d.get('components') or {}
pt = d.get('provider_tool_count')
final = comp.get('final')
tool_defs = comp.get('tool_definitions')
print(f'{pt if pt is not None else \"?\"}|{final if final is not None else \"?\"}|{tool_defs if tool_defs is not None else \"?\"}')
")"
    echo "baseline=$BASELINE in=${base_in:-?} provider_tools=${base_pt} comp_final=${base_final} tool_defs=${base_tool_defs}"
    echo "new=$NEW in=0 (no diagnostic; rate_limit — quota blocked)"
    echo "delta_in=skipped (no diagnostic on new turn)"
    exit 0
  fi
  echo "No diagnostic event found in: $NEW" >&2
  exit 1
fi
_extract_in() {
  echo "$1" | awk '{
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^in=[0-9]+$/) { sub(/^in=/, "", $i); print $i; exit }
    }
  }'
}
_p0_metrics() {
  "$PYTHON" "$EXTRACT" --file "$1" --json | "$PYTHON" -c "
import json, sys
d = json.load(sys.stdin)
comp = d.get('components') or {}
pt = d.get('provider_tool_count')
final = comp.get('final')
tool_defs = comp.get('tool_definitions')
print(f'{pt if pt is not None else \"?\"}|{final if final is not None else \"?\"}|{tool_defs if tool_defs is not None else \"?\"}')
"
}
base_in=$(_extract_in "$base_line")
new_in=$(_extract_in "$new_line")
IFS='|' read -r base_pt base_final base_tool_defs <<< "$(_p0_metrics "$BASELINE")"
IFS='|' read -r new_pt new_final new_tool_defs <<< "$(_p0_metrics "$NEW")"

echo "baseline=$BASELINE in=${base_in:-?} provider_tools=${base_pt} comp_final=${base_final} tool_defs=${base_tool_defs}"
echo "new=$NEW in=${new_in:-?} provider_tools=${new_pt} comp_final=${new_final} tool_defs=${new_tool_defs}"
if [[ "${new_in:-}" == "0" ]]; then
  echo "delta_in=skipped (new turn in=0 — quota or incomplete; use 01-no-tools-after-p0.jsonl for live delta)"
  exit 0
fi
if [[ -n "${base_in:-}" && -n "${new_in:-}" && "$base_in" =~ ^[0-9]+$ && "$new_in" =~ ^[0-9]+$ ]]; then
  echo "delta_in=$((new_in - base_in))"
  if [[ "$base_final" =~ ^[0-9]+$ && "$new_final" =~ ^[0-9]+$ ]]; then
    echo "delta_comp_final=$((new_final - base_final))"
  fi
fi
