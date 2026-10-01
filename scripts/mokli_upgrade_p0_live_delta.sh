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

read -r _ base_line <<<"$("$PYTHON" "$EXTRACT" --file "$BASELINE")"
read -r _ new_line <<<"$("$PYTHON" "$EXTRACT" --file "$NEW")"
base_in=$(echo "$base_line" | sed -n 's/.*in=\([0-9]*\).*/\1/p')
new_in=$(echo "$new_line" | sed -n 's/.*in=\([0-9]*\).*/\1/p')
echo "baseline=$BASELINE in=${base_in:-?}"
echo "new=$NEW in=${new_in:-?}"
if [[ -n "${base_in:-}" && -n "${new_in:-}" && "$base_in" =~ ^[0-9]+$ && "$new_in" =~ ^[0-9]+$ ]]; then
  echo "delta_in=$((new_in - base_in))"
fi
