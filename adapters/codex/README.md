# Codex 适配

Codex 原生支持 `~/.codex/skills/` 目录，结构与 Claude Code 一致。

## 安装

**Linux / macOS**（或 Git Bash）：

```bash
mkdir -p ~/.codex/skills/xizi-rujin
cp SKILL.md ~/.codex/skills/xizi-rujin/SKILL.md
```

**Windows PowerShell**：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills\xizi-rujin" | Out-Null
Copy-Item SKILL.md "$env:USERPROFILE\.codex\skills\xizi-rujin\SKILL.md" -Force
```

## 触发

Codex 重启后自动发现。输入 `/xizi` / `/wenyan` / `/heihua`，或说「省 token / 惜字」即触发。
