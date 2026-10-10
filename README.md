# 惜字如金 · xizi-rujin

> 拦截假绿——当 AI 声称「测试全过了」，先问：**没红过的绿，都是假绿。**
> 老审计：我不是不信你，我是不信没跑过的东西。

---

## 假绿灯演示（真实，30 秒看懂）

一个"测试全过"的模块：

```python
# demo_math.py
def add(a, b):
    return a + b
```

```python
# test.py —— 测试全过了 ✅
assert True
```

**老审计上工**（确定性工具，零 LLM）：

```
$ python -m eval.mutation_test demo_math.py --cmd "python test.py"
  变异体  1 [line 2 return x → return None]: 存活——假绿！✗
  变异体  2 [line 2 + → -]: 存活——假绿！✗

变异得分：0/2（0%）——通过阈值 80%；被杀=测试真能抓 bug；存活=假绿

结论：打回——测试抓不住任何 bug，这个「通过」不算数。
```

同模块换成真断言（`assert add(1,2) == 3`）→ 变异得分 100%，工具打印「结论：通过——变异得分 100% 达到通过阈值 80%。」

---

## 核心：三问 + 硬工具

**老审计三问**（方法论出处：TDD 红绿循环 · Kent Beck；变异测试 · DeMillo 1978；审计准则「反向证据」「工作底稿」）：

1. **红过吗？**——断言改坏之后，真的会红吗？
2. **错的抓得住吗？**——放一个必错样本，真的被抓住吗？
3. **挂的那些呢？**——失败的那些，逐条在哪里？

**硬工具**（确定性、零 LLM、零外部依赖，`eval/` 下）：

| 工具 | 干什么 |
|---|---|
| `fake_green.py` | AST 静态扫：恒真 / 跳过 / xfail / 吞异常 / 无断言 / 同源，以及真值断言、恒真比较、不可达断言、mock 被测对象。目录认 `test*.py` 和 `*_test.py`；一个测试文件都没扫到是「无法判定」 |
| `mutation_test.py` | 比较符（含边界）、四则和地板除、and/or、布尔、非零数字 +1、字符串追加 XX、return None、比较式 return True、赋值 None、去掉零参方法、else 名字换成 None。通过线只有 `PASS_THRESHOLD`（80%），CLI 和 bench 组 4 共用；基线不绿输出「无法判定」 |
| `bench.py` | 假绿陷阱集 + 四组对照（错误放行率） |

**人格入口**：`SKILL.md`（显示名老审计，技能名 `xizi-rujin`）——触发、引导、三态结论（通过 / 有条件通过 / 打回），证据强制：没命令+输出摘录不许写"已验证"。

---

## 安装

国内网络下优先用离线包：`bash install.sh` 把 `SKILL.md` 和工具链一起拷进本机 harness，不访问 PyPI。检测到哪个命令就装到哪：

| harness | 目录 |
|---|---|
| Claude Code（`claude` 在 PATH 上） | `~/.claude/skills/xizi-rujin/` |
| Codex（`codex` 在 PATH 上） | `~/.codex/skills/xizi-rujin/` |
| opencode | `${OPENCODE_CONFIG:-~/.config/opencode}/skills/xizi-rujin/` |

装完重启 harness。声称「测试全过 / 已验证」时，老审计跑的是技能目录里的入口，不是用户项目里的 `python -m eval`。

要让「声称通过」过不了关，而不是只靠模型自己想起审计，加 `--hook`。它把 Stop 钩子合并进现有配置，不覆盖别的键；再跑一次会跳过已经登记过的条目。卸掉只删我们的条目：

```bash
bash install.sh --hook project          # 当前目录 .claude/settings.json 和 .codex/hooks.json
bash install.sh --hook user             # ~/.claude/settings.json 和 ~/.codex/hooks.json
python xizi_rujin.py uninstall-hook --scope project --harness both
```

Windows（PowerShell，不依赖 Git Bash）：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hook project
```

钩子写的是 exec 形式：`command` 是当前 `python` 的绝对路径，`args` 把 `hook-stop` 分开传，Windows 上不会去跑 `.cmd` 垫片。Claude Code 的说明见 [hooks](https://code.claude.com/docs/en/hooks) 和 [hooks guide](https://code.claude.com/docs/en/hooks-guide)。Codex 同样有 Stop，说明见 [Codex hooks](https://developers.openai.com/codex/hooks)；项目级钩子要在 `/hooks` 里信任之后才会跑。两边都不支持的时候，审查者手动跑：

```bash
python xizi_rujin.py audit --changed
```

GitHub 上可选，不进本仓库的必跑检查。把 `.github/workflows/xizi-audit.example.yml` 抄进自己的仓库，或直接用 `.github/actions/xizi-audit`。打回退出码 1，无法判定退出码 2，结论写在 job summary。

| 结论 | Stop 钩子 | `audit --changed` |
|---|---|---|
| 通过 | 静默放行 | 退出码 0 |
| 没有相关的 Python 改动 | 静默放行，不跑变异 | 退出码 0 |
| 打回 | `{"decision":"block","reason":"..."}`，退出码 0 | 退出码 1 |
| 无法判定（没测试、基线是红的、命令错） | 同样拦住，理由里写无法判定 | 退出码 2 |
| 钩子自己崩了、git 不可用 | 放行，`systemMessage` 里写明 | 退出码 2 |
| `stop_hook_active: true`，或同一会话已拦住 3 次 | 放行，避免死循环 | — |

拦截次数记在系统临时目录（或 `XIZI_STOP_HOOK_STATE_DIR`），不写进工作区。Claude Code 自己还有连续 8 次拦住的上限。

技能目录里的三条命令：

```bash
python "$SKILL_DIR/xizi_rujin.py" scan <测试文件或目录>
python "$SKILL_DIR/xizi_rujin.py" mutate <源文件.py> --cmd "<测试命令>"
python "$SKILL_DIR/xizi_rujin.py" audit --source <源文件.py> --cmd "<测试命令>" <测试文件或目录>
```

仓库开发，或本机有 `uv`、能访问 GitHub 时，也可以不装技能、直接跑控制台入口（仍不需要发到 PyPI）：

```bash
uvx --from git+https://github.com/qlheric/xizi-rujin xizi-rujin scan <测试文件或目录>
uvx --from git+https://github.com/qlheric/xizi-rujin xizi-rujin mutate <源文件.py> --cmd "<测试命令>"
```

## 用法（在本仓库里）

```bash
python -m eval.fake_green tests              # 静态扫作弊模式
python -m eval.mutation_test <src> --cmd "<测试命令>"   # 变异测假绿
python xizi_rujin.py audit --source <src> --cmd "<测试命令>" <测试文件或目录>
python -m xizi_rujin audit --changed          # 只审工作区里改过的 Python
python -m eval.bench --dir eval/traps_v2 --llm --engine qwen   # 四组对照（要自己的 LLM key）
```

---

## benchmark（四组对照，v2 陷阱 × qwen 弱模型）

| 组 | 错误放行率 |
|---|---|
| 组 1 原始 LLM | 10/10（100%，轻信"测试通过"） |
| 组 2 加「认真检查」 | 3/10（30%） |
| 组 3 老审计人格 | 0/10（0%，三问全打回） |
| 组 4 工具链（确定性） | 1/10（10%） |

**归因**：价值主要来自**方法论三问**（100%→0%）；工具链的价值是**确定性证据**（可复现、零幻觉），不是独立判定。

---

## 诚实说明（已知盲区）

- 工具链在 v2 上放行 **1/10**。剩下的 `v2_07` 源码没有 bug，测试只覆盖两个能整除的点：五个变异里四个被杀，只剩 `/ → //` 存活，80% 仍过线。v1 放行 **1/10**，剩下的 `trap_06` 是 oracle 和实现互相钉死（`discount(100) == 80` 对上 `price * 0.8`），没有未测分支。组 1–3 仍是当时 qwen 的记录。
- 强模型（deepseek 级）本身就会审计，组 1-3 分不出差别——工具链的差异化是「确定性」，不是「比 LLM 聪明」。
- 真实抓出过的假绿见 [假绿灯档案](docs/fake-green-archive.md)（6 篇真实案例）。

## License

MIT
