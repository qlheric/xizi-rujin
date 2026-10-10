#!/usr/bin/env bash
# 惜字如金 · 把技能正文和离线工具链装进本机已装的 coding agent harness
# 用法：bash install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="xizi-rujin"
installed=0

install_to() {
  local label="$1" dest_dir="$2"
  mkdir -p "$dest_dir/xizi_rujin" "$dest_dir/eval"
  cp "$HERE/SKILL.md" "$dest_dir/SKILL.md"
  cp "$HERE/xizi_rujin.py" "$dest_dir/xizi_rujin.py"
  cp "$HERE/xizi_rujin/__init__.py" "$dest_dir/xizi_rujin/__init__.py"
  cp "$HERE/xizi_rujin/__main__.py" "$dest_dir/xizi_rujin/__main__.py"
  cp "$HERE/xizi_rujin/cli.py" "$dest_dir/xizi_rujin/cli.py"
  cp "$HERE/eval/__init__.py" "$dest_dir/eval/__init__.py"
  cp "$HERE/eval/fake_green.py" "$dest_dir/eval/fake_green.py"
  cp "$HERE/eval/mutation_test.py" "$dest_dir/eval/mutation_test.py"
  echo "✓ $label → $dest_dir"
  installed=1
}

if command -v claude >/dev/null 2>&1; then
  install_to "Claude Code" "$HOME/.claude/skills/$NAME"
fi

if command -v codex >/dev/null 2>&1; then
  install_to "Codex" "$HOME/.codex/skills/$NAME"
fi

if command -v opencode >/dev/null 2>&1; then
  install_to "opencode" "${OPENCODE_CONFIG:-$HOME/.config/opencode}/skills/$NAME"
fi

if [ "$installed" -eq 0 ]; then
  echo "未检测到 claude / codex / opencode。请手动把技能目录复制到对应 harness（见 adapters/）。"
  exit 1
fi

echo "安装完成。重启 harness 后，声称「测试全过 / 已验证」时，老审计会用技能目录里的 xizi_rujin.py 核对。"
