#!/usr/bin/env bash
# Install tracked Cursor skills from cursor-skills/ into ~/.cursor/skills/
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SRC="$REPO_ROOT/cursor-skills"
DEST="$HOME/.cursor/skills"

mkdir -p "$DEST"

for skill_dir in "$SRC"/*/; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  ln -sfn "$skill_dir" "$DEST/$name"
  echo "linked $DEST/$name -> $skill_dir"
done

chmod -R a+rX "$DEST" 2>/dev/null || true
echo "Installed $(find "$SRC" -mindepth 1 -maxdepth 1 -type d | wc -l) skill(s) to $DEST"
