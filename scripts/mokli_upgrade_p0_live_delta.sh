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
new_line="$("$PYTHON" "$EXTRACT" --file "$NEW")"
_extract_in() {
  echo "$1" | awk '{
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^in=[0-9]+$/) { sub(/^in=/, "", $i); print $i; exit }
    }
  }'
}
base_in=$(_extract_in "$base_line")
new_in=$(_extract_in "$new_line")
echo "baseline=$BASELINE in=${base_in:-?}"
echo "new=$NEW in=${new_in:-?}"
if [[ -n "${base_in:-}" && -n "${new_in:-}" && "$base_in" =~ ^[0-9]+$ && "$new_in" =~ ^[0-9]+$ ]]; then
  echo "delta_in=$((new_in - base_in))"
fi
