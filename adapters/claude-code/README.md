# Claude Code 适配

技能名 `xizi-rujin`，正文里的人格是老审计。`bash install.sh` 会在检测到 `claude` 时，把技能和离线工具链一起放到 `~/.claude/skills/xizi-rujin/`。

## 安装

在仓库根目录：

```bash
bash install.sh
```

手动复制（Linux / macOS / Git Bash）等价于脚本做的事：

```bash
mkdir -p ~/.claude/skills/xizi-rujin/xizi_rujin ~/.claude/skills/xizi-rujin/eval
cp SKILL.md xizi_rujin.py ~/.claude/skills/xizi-rujin/
cp xizi_rujin/__init__.py xizi_rujin/__main__.py xizi_rujin/cli.py ~/.claude/skills/xizi-rujin/xizi_rujin/
cp eval/__init__.py eval/fake_green.py eval/mutation_test.py ~/.claude/skills/xizi-rujin/eval/
```

**Windows PowerShell**：

```powershell
$dest = "$env:USERPROFILE\.claude\skills\xizi-rujin"
New-Item -ItemType Directory -Force "$dest\xizi_rujin", "$dest\eval" | Out-Null
Copy-Item SKILL.md, xizi_rujin.py $dest
Copy-Item xizi_rujin\__init__.py, xizi_rujin\__main__.py, xizi_rujin\cli.py "$dest\xizi_rujin"
Copy-Item eval\__init__.py, eval\fake_green.py, eval\mutation_test.py "$dest\eval"
```

## 触发

重启 Claude Code。技能名是 `xizi-rujin`。当对话里出现「完成 / 通过 / 全绿 / 已验证」时，老审计用技能目录里的 `xizi_rujin.py` 核对，不要求用户项目安装任何包。
