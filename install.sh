#!/usr/bin/env bash
# 惜字如金 · 把技能正文和离线工具链装进本机已装的 coding agent harness
# 用法：
#   bash install.sh
#   bash install.sh --hook project
#   bash install.sh --hook user
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="xizi-rujin"
installed=0
HOOK_SCOPE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --hook)
      HOOK_SCOPE="${2:-}"
      if [ -z "$HOOK_SCOPE" ]; then
        echo "--hook 需要 project 或 user"
        exit 2
      fi
      shift 2
      ;;
    --hook=*)
      HOOK_SCOPE="${1#*=}"
      shift
      ;;
    *)
      echo "未知参数：$1"
      exit 2
      ;;
  esac
done

if [ -n "$HOOK_SCOPE" ] && [ "$HOOK_SCOPE" != "project" ] && [ "$HOOK_SCOPE" != "user" ]; then
  echo "--hook 只能是 project 或 user，收到：$HOOK_SCOPE"
  exit 2
fi

install_to() {
  local label="$1" dest_dir="$2"
  mkdir -p "$dest_dir/xizi_rujin" "$dest_dir/eval"
  cp "$HERE/SKILL.md" "$dest_dir/SKILL.md"
  cp "$HERE/xizi_rujin.py" "$dest_dir/xizi_rujin.py"
  cp "$HERE/xizi_rujin/__init__.py" "$dest_dir/xizi_rujin/__init__.py"
  cp "$HERE/xizi_rujin/__main__.py" "$dest_dir/xizi_rujin/__main__.py"
  cp "$HERE/xizi_rujin/cli.py" "$dest_dir/xizi_rujin/cli.py"
  cp "$HERE/xizi_rujin/audit_changed.py" "$dest_dir/xizi_rujin/audit_changed.py"
  cp "$HERE/xizi_rujin/stop_hook.py" "$dest_dir/xizi_rujin/stop_hook.py"
  cp "$HERE/xizi_rujin/install_hook.py" "$dest_dir/xizi_rujin/install_hook.py"
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

if [ "$installed" -eq 0 ] && [ -z "$HOOK_SCOPE" ]; then
  echo "未检测到 claude / codex / opencode。请手动把技能目录复制到对应 harness（见 adapters/）。"
  exit 1
fi

# Git Bash 里 $PWD 是 /c/Users/...。Windows 上的 python.exe 不认这种路径，先转回盘符。
win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

pick_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if [ -n "$HOOK_SCOPE" ]; then
  if ! PY="$(pick_python)"; then
    echo "注册钩子需要 Python。"
    exit 1
  fi
  "$PY" "$(win_path "$HERE/xizi_rujin.py")" install-hook \
    --scope "$HOOK_SCOPE" --harness both --project "$(win_path "$PWD")"
fi

if [ "$installed" -eq 0 ]; then
  echo "未检测到 claude / codex / opencode。钩子已按 $HOOK_SCOPE 注册。"
  exit 0
fi

echo "安装完成。重启 harness 后，声称「测试全过 / 已验证」时，老审计会用技能目录里的 xizi_rujin.py 核对。"
