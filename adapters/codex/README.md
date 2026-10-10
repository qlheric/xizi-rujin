# Codex 适配

Codex 的技能目录是 `~/.codex/skills/`，结构和 Claude Code 一样。`bash install.sh` 在检测到 `codex` 时写入 `~/.codex/skills/xizi-rujin/`。

## 安装

在仓库根目录：

```bash
bash install.sh
```

手动复制（Linux / macOS / Git Bash）：

```bash
mkdir -p ~/.codex/skills/xizi-rujin/xizi_rujin ~/.codex/skills/xizi-rujin/eval
cp SKILL.md xizi_rujin.py ~/.codex/skills/xizi-rujin/
cp xizi_rujin/__init__.py xizi_rujin/__main__.py xizi_rujin/cli.py ~/.codex/skills/xizi-rujin/xizi_rujin/
cp eval/__init__.py eval/fake_green.py eval/mutation_test.py ~/.codex/skills/xizi-rujin/eval/
```

**Windows PowerShell**：

```powershell
$dest = "$env:USERPROFILE\.codex\skills\xizi-rujin"
New-Item -ItemType Directory -Force "$dest\xizi_rujin", "$dest\eval" | Out-Null
Copy-Item SKILL.md, xizi_rujin.py $dest
Copy-Item xizi_rujin\__init__.py, xizi_rujin\__main__.py, xizi_rujin\cli.py "$dest\xizi_rujin"
Copy-Item eval\__init__.py, eval\fake_green.py, eval\mutation_test.py "$dest\eval"
```

## 触发

重启 Codex。技能名是 `xizi-rujin`。当对话里出现「完成 / 通过 / 全绿 / 已验证」时，老审计用技能目录里的 `xizi_rujin.py` 核对。

## Stop 钩子

Codex 有 Stop 钩子，字段和 Claude Code 同一套：stdin JSON，`stop_hook_active`，退出码 0 时 stdout 必须是 JSON，`decision: block` 会让这一轮继续。见 [Codex hooks](https://developers.openai.com/codex/hooks)。

```bash
bash install.sh --hook project
```

项目级写 `.codex/hooks.json`，用户级写 `~/.codex/hooks.json`。不写 `config.toml`，避免两份配置叠在一起。项目级钩子要先在 `/hooks` 里信任才会跑。不要加 `continue: false`，那个会直接把这一轮停掉，而不是把打回的理由交回去。

钩子没被信任、或这版 Codex 还不认 hooks 时，审查者自己跑并把输出贴进验收：

```bash
python xizi_rujin.py audit --changed
```

通过、打回、无法判定的退出码是 0、1、2。
