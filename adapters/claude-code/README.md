# Claude Code 适配

「惜字如金」的 SKILL.md 就是唯一正文，Claude Code 原生支持 `skills/` 目录。

## 安装

**Linux / macOS**（或 Git Bash）：

```bash
mkdir -p ~/.claude/skills/xizi-rujin
cp SKILL.md ~/.claude/skills/xizi-rujin/SKILL.md
```

**Windows PowerShell**：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\xizi-rujin" | Out-Null
Copy-Item SKILL.md "$env:USERPROFILE\.claude\skills\xizi-rujin\SKILL.md" -Force
```

## 触发

Claude Code 重启后自动发现 skill。输入 `/xizi`（惜字档）、`/wenyan`（文言档）、`/heihua`（黑话档），或说「省 token / 说短点 / 惜字」即触发。
