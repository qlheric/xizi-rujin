<p align="center">
  <img src="assets/logo.svg" alt="惜字如金" width="160">
</p>

# 惜字如金 · xizi-rujin

> **没红过的绿，都是假绿。**
>
> AI 说「测试全过了」的时候，老审计用三问和一套确定性工具链核对这个「通过」。说服不够，就在它停下来之前拦住。

---

## 30 秒看懂

`demo_math.py`：

<!-- file:demo_math.py:start -->
```python
def add(a, b):
    return a + b
```
<!-- file:demo_math.py:end -->

`test.py`，自己是绿的：

<!-- file:test.py:start -->
```python
assert True
```
<!-- file:test.py:end -->

```bash
python -m eval.mutation_test demo_math.py --cmd "python test.py"
```

<!-- demo-fake:start -->
```text
  变异体  1 [line 2 return x → return None]: 存活——假绿！✗
  变异体  2 [line 2 + → -]: 存活——假绿！✗

变异得分：0/2（0%）——通过阈值 80%；被杀=测试真能抓 bug；存活=假绿

结论：打回——测试抓不住任何 bug，这个「通过」不算数。
```
<!-- demo-fake:end -->

换成真断言（`test_real.py`）：

<!-- file:test_real.py:start -->
```python
from demo_math import add
assert add(1, 2) == 3
```
<!-- file:test_real.py:end -->

```bash
python -m eval.mutation_test demo_math.py --cmd "python test_real.py"
```

<!-- demo-real:start -->
```text
  变异体  1 [line 2 return x → return None]: 被杀 ✓
  变异体  2 [line 2 + → -]: 被杀 ✓

变异得分：2/2（100%）——通过阈值 80%；被杀=测试真能抓 bug；存活=假绿

结论：通过——变异得分 100% 达到通过阈值 80%。
```
<!-- demo-real:end -->

同一份 `test.py` 用静态扫描也能直接打回：

```bash
python -m eval.fake_green test.py
```

<!-- demo-scan:start -->
```text
扫描了 1 个测试文件，发现 1 处疑似假绿：
  ✗ [assert_true] test.py:1 — 恒真断言——永远绿: assert True
```
<!-- demo-scan:end -->

一个测试文件都没有：

```bash
python -m eval.fake_green empty
```

<!-- demo-empty:start -->
```text
无法判定：没有扫描到测试文件（约定 test*.py 与 *_test.py）。
```
<!-- demo-empty:end -->

退出码：通过 0，打回 1，无法判定 2。

---

## 它解决什么

编程代理会把「命令退出码是 0」写成「已经验证」。`assert True`、跳过的测试、和实现钉死的错误期望，都会给出这种绿。惜字如金只做一件事：这个绿有没有能力变红。它不评代码风格。

人格在 `SKILL.md`（技能名 `xizi-rujin`，显示名老审计）。证据在工具里：没命令、没输出，不许写「已验证」。

## 三问

1. **红过吗？** 断言改坏之后，会红吗？
2. **错的抓得住吗？** 放一个必错样本，它被抓住了吗？
3. **挂的那些呢？** 没被抓住的变异，逐条在哪里？

出处：TDD 红绿循环（Kent Beck），变异测试（DeMillo 1978），审计里的反向证据和工作底稿。

## 怎么判定

三步都是确定性的，零 LLM，零第三方依赖。通过线只有 `eval/mutation_test.py` 里的 `PASS_THRESHOLD`（0.8）。CLI、技能和下面的组 4 都读这一处。

| 步骤 | 做什么 | 不算通过的情况 |
|---|---|---|
| 基线 | 先跑你原来的测试 | 测试本来就是红的、命令写错、超时。结论是无法判定 |
| AST 扫描 | 扫 `test*.py` 和 `*_test.py`：恒真断言、跳过、xfail、吞异常、无断言、左右同源、恒真比较、不可达断言、mock 被测对象 | 扫到这些模式就是打回。一个测试文件都没有是无法判定，退出码 2 |
| 变异 | 改比较符、四则和地板除、and/or、布尔、非零数字 +1、字符串、`return None`、去掉零参调用等，再跑测试 | 被杀掉的比例低于 80% 是打回。没有变异点是无法判定 |

`audit` 先扫描再变异。扫描已经无法判定就停。扫描看见假绿时，变异得分过线也不能单独算通过。

| 结论 | 含义 | 退出码 |
|---|---|---|
| 通过 | 扫描干净，变异得分 ≥ 80% | 0 |
| 打回 | 假绿，或得分低于 80% | 1 |
| 无法判定 | 没测试、基线不绿、没有变异点、命令错 | 2 |

无法判定是「这次没有证据」，退出码不是 0。

## 安装

国内网络用离线包，不访问 PyPI。脚本发现哪个命令在 PATH 上，就把技能和工具链拷到哪。

| harness | 目录 |
|---|---|
| Claude Code | `~/.claude/skills/xizi-rujin/` |
| Codex | `~/.codex/skills/xizi-rujin/` |
| opencode | `${OPENCODE_CONFIG:-~/.config/opencode}/skills/xizi-rujin/` |

macOS / Linux / Git Bash：

```bash
bash install.sh                  # 只装技能
bash install.sh --hook project   # 再登记当前仓库的 Stop 钩子
bash install.sh --hook user      # 登记到用户级配置，对所有仓库生效
```

Windows PowerShell（不依赖 Git Bash）：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hook project
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Hook user
```

`--hook` / `-Hook` 只接受 `project` 或 `user`。它把钩子合并进现有 JSON，不覆盖别的键；同一条再装一次不会重复。卸掉只删我们的条目：

```bash
python xizi_rujin.py uninstall-hook --scope project --harness both
```

`--scope` 是 `project` 或 `user`。`--harness` 是 `claude`、`codex` 或 `both`（默认 `both`）。

- `project`：`.claude/settings.json` 和 `.codex/hooks.json`
- `user`：`~/.claude/settings.json` 和 `~/.codex/hooks.json`

钩子是 exec 形式：`command` 为当前 Python 的绝对路径，`args` 分开传 `hook-stop`。Windows 上不会去跑 `.cmd` 垫片。装完重启 harness。

本机有 `uv`、能访问 GitHub 时，也可以不装技能：

```bash
uvx --from git+https://github.com/qlheric/xizi-rujin xizi-rujin audit --changed
```

## Stop 钩子

Claude Code 和 Codex 结束这一轮时，钩子只审这次改过的 Python：相对 HEAD 的已暂存、未暂存、未跟踪文件；变异只打到改动所在的函数。Codex 的项目级钩子要先在 `/hooks` 里信任。字段以两边的文档为准：[Claude Code hooks](https://code.claude.com/docs/en/hooks)，[Codex hooks](https://developers.openai.com/codex/hooks)。

| 情况 | 行为 |
|---|---|
| 通过 | 静默放行 |
| 没有相关的 Python 改动 | 静默放行，不跑变异 |
| 打回 | 退出码 0，`{"decision":"block","reason":"中文理由"}` |
| 无法判定（没测试、基线是红的、没有变异点） | 同样拦住，理由里写无法判定 |
| `stop_hook_active` 为 true | 放行，避免钩子把自己再叫起来 |
| 同一会话已经拦住 3 次 | 放行。次数在系统临时目录，不写进工作区 |
| `background_tasks` 非空 | 这一轮还没真停，放行 |
| 钩子自己出错，或 git 不可用 | 放行，`systemMessage` 说明原因 |

拦住用退出码 0 加 JSON，不混用退出码 2。不输出 `continue: false`。opencode 只装技能，没有钩子配置。

## 审查者手动跑

Codex 当「脑子」验收 Claude Code 的交付时，把下面的输出贴进审查：

```bash
python -m xizi_rujin audit --changed
python -m xizi_rujin audit --changed --base origin/main
```

`--base` 用三点 diff（`base...HEAD`），给 PR 用。不写 `--base` 时看工作区相对 HEAD 的改动。退出码与上表相同：通过 0，打回 1，无法判定 2。git 不可用时 CLI 打印无法判定并退出 2。

技能目录里的入口是同一套命令，把 `python -m xizi_rujin` 换成 `python "$SKILL_DIR/xizi_rujin.py"`：

```bash
python "$SKILL_DIR/xizi_rujin.py" scan <测试文件或目录>
python "$SKILL_DIR/xizi_rujin.py" mutate <源文件.py> --cmd "<测试命令>"
python "$SKILL_DIR/xizi_rujin.py" audit --source <源文件.py> --cmd "<测试命令>" <测试文件或目录>
python "$SKILL_DIR/xizi_rujin.py" audit --changed
```

## GitHub Action

可选。本仓库自带的示例 `.github/workflows/xizi-audit.example.yml` 只挂 `workflow_dispatch`，不挡这里的 pull request。抄到自己的仓库时改成 `pull_request`：

```yaml
name: xizi-audit
on:
  pull_request:
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: qlheric/xizi-rujin/.github/actions/xizi-audit@main
        with:
          base: origin/main
```

动作跑 `audit --changed`。打回退出码 1，无法判定退出码 2，结论追加到 job summary。`timeout` 是单条测试命令的秒数，默认 60。

## 基准

组 4 是这次在本仓库重跑的，不调用模型。v1、v2 各 10 个陷阱，错误放行都是 **1/10**。

| 集 | 错误放行 | 漏掉的那一个 |
|---|---|---|
| v1 `eval/traps` | 1/10 | `trap_06_hardcode_wrong` |
| v2 `eval/traps_v2` | 1/10 | `v2_07_avg_pos` |

`trap_06` 的实现是 `price * 0.8`，测试写死 `discount(100) == 80`。三个变异（`return None`、`* → /`、`0.8 → 1.8`）都被杀掉，得分 100%。oracle 和实现互相钉死，没有未测分支。

`v2_07` 的实现是 `(a + b) / 2`，测试只覆盖两个能整除的点。五个变异里四个被杀，`/ → //` 还活着，4/5 = 80%，刚好过线。测过 `avg(1, 2) == 1.5` 的对照会杀掉地板除。

组 1–3 是当时 qwen 弱模型的历史记录，依赖 LLM，这次没有重跑：原始模型 10/10 放行，加一句「认真检查」3/10，老审计人格 0/10。强模型自己就会审计，那三组拉不开差距。工具链的差异是可复现，不是比模型聪明。

## 局限

- 目前只审计 Python。
- 硬编码的错误期望（`trap_06`）和刚好卡在 80% 的窄测试（`v2_07`）会放行。通过线不为此下调。
- `tests/` 里只按 `test_<模块>.py`、`<模块>_test.py` 配对。文件名对不上、又没有同目录测试，结论是无法判定。
- 钩子超时默认 120 秒。超时后 harness 丢掉输出并放行，避免卡死会话。
- 老版本 Codex 可能另要特性开关。官方文档没有把它写成必需项，安装器不写进 `config.toml`。

真实案例见 [假绿灯档案](docs/fake-green-archive.md)。

## 常见问题

**80% 能改吗？** 能，在 `PASS_THRESHOLD` 改一处。不要在技能、CLI、基准里各写一个数。

**基线是红的，为什么不打 0 分？** 测试本来就没过，变异得分没有分母。这是无法判定。

**钩子会不会死循环？** `stop_hook_active` 为真时立刻放行。同一会话默认最多拦住 3 次（`XIZI_STOP_HOOK_MAX_BLOCKS`）。Claude Code 自己还有连续拦住的上限。

**Windows 上 `bash install.sh` 没反应？** 用 Git Bash，或直接跑 `install.ps1`。`System32\bash.exe` 在没装 WSL 发行版时不是安装器。

**opencode 呢？** 有技能，没有 Stop 钩子。验收用 `audit --changed`。

## English

xizi-rujin is an anti-fake-green auditor for AI coding agents. A green run that was never red does not count. Three questions (did it fail first, can it catch a planted bug, where are the survivors) sit on a deterministic toolchain: the baseline must pass, an AST scan rejects fake asserts, and mutation testing must kill at least 80% of mutants. Claude Code and Codex Stop hooks block the turn on 打回 or 无法判定. Reviewers can run `xizi-rujin audit --changed`. A GitHub Action does the same for a pull request. Python only. Group 4 of the bench lets 1/10 traps through on both suites (`trap_06_hardcode_wrong`, `v2_07_avg_pos`).

## License

MIT
