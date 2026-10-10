# opencode 适配

opencode 的 skills 目录为 `~/.config/opencode/skills/`（也可用 `OPENCODE_CONFIG`）。`bash install.sh` 在检测到 `opencode` 时，把技能和离线工具链一起放进去。

## 安装

```bash
bash install.sh
```

手动复制：

```bash
dest="${OPENCODE_CONFIG:-$HOME/.config/opencode}/skills/xizi-rujin"
mkdir -p "$dest/xizi_rujin" "$dest/eval"
cp SKILL.md xizi_rujin.py "$dest/"
cp xizi_rujin/__init__.py xizi_rujin/__main__.py xizi_rujin/cli.py "$dest/xizi_rujin/"
cp eval/__init__.py eval/fake_green.py eval/mutation_test.py "$dest/eval/"
```

## 触发

重启 opencode。技能名是 `xizi-rujin`。当对话里出现「完成 / 通过 / 全绿 / 已验证」时，老审计用技能目录里的 `xizi_rujin.py` 核对。

> 注：opencode 未在本机实测（开发机未安装 opencode CLI），此适配为文档对齐，欢迎用户反馈。
