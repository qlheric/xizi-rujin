# opencode 适配

opencode 的 skills 目录为 `~/.config/opencode/skills/`（也可用项目级 `.opencode/skills/`）。

## 安装

```bash
mkdir -p "${OPENCODE_CONFIG:-$HOME/.config/opencode}/skills/xizi-rujin"
cp SKILL.md "${OPENCODE_CONFIG:-$HOME/.config/opencode}/skills/xizi-rujin/SKILL.md"
```

## 触发

opencode 重启后自动发现。输入 `/xizi` / `/wenyan` / `/heihua`，或说「省 token / 惜字」即触发。

> 注：opencode 未在本机实测（开发机未安装 opencode CLI），此适配为文档对齐，欢迎用户反馈。
