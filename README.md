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
| `mutation_test.py` | 变异 8 算子 + 变异得分。通过线只有 `PASS_THRESHOLD`（80%），CLI 退出码和 bench 组 4 共用；基线不绿输出「无法判定」 |
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

装完重启 harness。声称「测试全过 / 已验证」时，老审计跑的是技能目录里的入口，不是用户项目里的 `python -m eval`：

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
python -m eval.bench --dir eval/traps_v2 --llm --engine qwen   # 四组对照（要自己的 LLM key）
```

---

## benchmark（四组对照，v2 陷阱 × qwen 弱模型）

| 组 | 错误放行率 |
|---|---|
| 组 1 原始 LLM | 10/10（100%，轻信"测试通过"） |
| 组 2 加「认真检查」 | 3/10（30%） |
| 组 3 老审计人格 | 0/10（0%，三问全打回） |
| 组 4 工具链（确定性） | 4/10（40%） |

**归因**：价值主要来自**方法论三问**（100%→0%）；工具链的价值是**确定性证据**（可复现、零幻觉），不是独立判定。

---

## 诚实说明（已知盲区）

- 工具链的 40% 放行 = **硬编码错误期望**（测试 oracle 本身=bug 输出，变异测不出——变异测试的原理性盲区）+ 变异点落在被测路径外。
- 强模型（deepseek 级）本身就会审计，组 1-3 分不出差别——工具链的差异化是「确定性」，不是「比 LLM 聪明」。
- 真实抓出过的假绿见 [假绿灯档案](docs/fake-green-archive.md)（6 篇真实案例）。

## License

MIT
