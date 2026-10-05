#!/usr/bin/env bash
# 惜字如金 · 安装到本机已装的 coding agent harness
# 用法：bash install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$HERE/SKILL.md"
NAME="xizi-rujin"
installed=0

install_to() {
  local label="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  cp "$SKILL_SRC" "$dest"
  echo "✓ $label → $dest"
  installed=1
}

if command -v claude >/dev/null 2>&1; then
  install_to "Claude Code" "$HOME/.claude/skills/$NAME/SKILL.md"
fi

if command -v codex >/dev/null 2>&1; then
  install_to "Codex" "$HOME/.codex/skills/$NAME/SKILL.md"
fi

if command -v opencode >/dev/null 2>&1; then
  install_to "opencode" "${OPENCODE_CONFIG:-$HOME/.config/opencode}/skills/$NAME/SKILL.md"
fi

if [ "$installed" -eq 0 ]; then
  echo "未检测到 claude / codex / opencode。请手动复制 SKILL.md 到对应 harness 的 skills 目录（见 adapters/）。"
  exit 1
fi

echo "安装完成。重启 harness 后，输入 /xizi 或说「省 token / 惜字」即可触发。"
