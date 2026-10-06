# Awesome 收录提交清单（放大器）

> 目标：被高星 awesome 列表收录 = 第三方背书（对标 caveman 的 Adobe/JetBrains 引用）。
> 状态：调研完成，条目已备好；提交 PR 需 qlheric 账号操作。

## 目标列表（按相关性排序）

| # | 仓库 | 星 | 分类 | 为什么 |
|---|---|---|---|---|
| 1 | [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 35.2k | Context Engineering | 最对口：agent skills 精选集，有 context/token 分类 |
| 2 | [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15.3k | Community Skills | 有 CONTRIBUTING.md，明确接受 PR，最易提交 |
| 3 | [AiHubCN/Awesome-Chinese-LLM](https://github.com/AiHubCN/Awesome-Chinese-LLM) | 高 | 中文 LLM | 中文空位差异化，中文社区背书 |
| 4 | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 55.1k | Skills | 流量最大 |

## 收录条目（每个列表的一句话描述）

**英文条目**（列表 1/2/4 用）：

> [xizi-rujin（惜字如金）](https://github.com/qlheric/xizi-rujin) — Chinese "token saver" meme skill: teaches coding agents to compress Chinese output with 文言/成语/23-domain jargon. Measured 37.9% token savings (tiktoken o200k) with payload verbatim protection; reproducible eval + red assertion + negative control.

**中文条目**（列表 3 用）：

> [惜字如金（xizi-rujin）](https://github.com/qlheric/xizi-rujin) — 中文版 caveman：教 coding agent 用文言/成语/23 领域黑话压缩中文输出，实测省 37.9%（tiktoken），payload/数字逐字符保留，可复现评测 + 能红断言 + 阴性对照。

## 提交步骤（每个列表）

1. fork 目标仓库到 `qlheric` 名下；
2. 在对应分类下加一行上述条目；
3. 提 PR（标题建议：`Add xizi-rujin — Chinese token saver skill`）。

## 补充：GitHub Topics（无门槛，立即做）

给 `xizi-rujin` 仓库 Settings → Topics 加上这些标签（提升 topic 页曝光）：

```
meme  prompt-engineering  skill  tokens  chinese  claude-code  codex  agent-skills  context-engineering
```
