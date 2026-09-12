#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.bun/bin:$PATH"

if ! command -v bun >/dev/null 2>&1; then
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

if [ ! -d "$HOME/gstack" ]; then
  git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git "$HOME/gstack"
fi

cd "$HOME/gstack"
./setup --host cursor

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir -p "$REPO_ROOT/.cursor/skills"

for skill_dir in "$HOME/gstack/.cursor/skills"/gstack*/; do
  ln -sfn "$skill_dir" "$REPO_ROOT/.cursor/skills/$(basename "$skill_dir")"
done

chmod -R a+rX "$HOME/.cursor/skills" 2>/dev/null || true

echo "gstack skills installed:"
ls "$REPO_ROOT/.cursor/skills" | rg '^gstack' | wc -l
