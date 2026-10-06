# Awesome 收录提交清单（放大器）

> 目标：被高星 awesome 列表收录 = 第三方背书（对标 caveman 的 Adobe/JetBrains 引用）。
> 状态：调研完成，精确插入行已核对格式；提交 PR 需 qlheric 账号操作。

## 目标列表（按提交顺序）

| # | 仓库 | 星 | 分类 | 格式 |
|---|---|---|---|---|
| 1 | [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15.3k | Community Skills → Individual Skills | 表格 |
| 2 | [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 35.2k | Context Engineering | 列表 |
| 3 | [AiHubCN/Awesome-Chinese-LLM](https://github.com/AiHubCN/Awesome-Chinese-LLM) | 高 | 中文 LLM | 待查 |
| 4 | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 55.1k | Skills | 待查 |

## 精确插入行（已核对格式）

### ① travisvn/awesome-claude-skills（表格格式）

位置：`## 🌟 Community Skills` → `### Individual Skills` 的表格里，加一行：

```markdown
| **[xizi-rujin](https://github.com/qlheric/xizi-rujin)** | Chinese "token saver" skill — teaches coding agents to compress Chinese output with 文言/成语/23-domain jargon; 37.9% token savings (tiktoken o200k) with payload verbatim protection |
```

### ② VoltAgent/awesome-agent-skills（列表格式）

位置：`Context Engineering` 折叠区（`<summary>Context Engineering</summary>` 下），加一行：

```markdown
- **[qlheric/xizi-rujin](https://github.com/qlheric/xizi-rujin)** - Chinese "token saver" meme skill: teaches coding agents to compress Chinese output with 文言/成语/23-domain jargon. 37.9% token savings (tiktoken o200k), payload verbatim, reproducible eval + red assertion + negative control
```

### ③④ 待查（AiHubCN / awesome-claude-code）

提交 ①② 后，再查这两个列表的格式（中文列表格式不同）。

## 提交步骤（每个列表）

1. fork 目标仓库到 `qlheric` 名下；
2. 在对应位置加上面那一行；
3. 提 PR（标题建议：`Add xizi-rujin — Chinese token saver skill`）。

## 补充：GitHub Topics（无门槛，立即做）

给 `xizi-rujin` 仓库 Settings → Topics 加上这些标签（提升 topic 页曝光）：

```
meme  prompt-engineering  skill  tokens  chinese  claude-code  codex  agent-skills  context-engineering
```
