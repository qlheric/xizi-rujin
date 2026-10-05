# 惜字如金 · xizi-rujin

<p align="center"><img src="assets/logo.svg" width="160" alt="惜字如金 logo"></p>

> *why use many token when one Chinese character do trick*

**中文版「省 token」meme skill** —— 教 coding agent 用「文言 / 成语 / 黑话」说话，把 prompt 的 token 砍掉一大截。

中文单字表意、四字成语、垂直黑话，是中文自带的压缩基因。caveman / ponytail 的英文版做不到。

---

## 三层压缩档

| 档 | 命令 | 风格 | 压缩率 |
|---|---|---|---|
| 文言档 | `/wenyan` | 文言文（之乎者也 + 单字） | 中 |
| 惜字档 | `/xizi` | 成语 + 极限单字 | 高 |
| 黑话档 | `/heihua` | A 股 / 垂直术语缩写 | 最高（领域化） |

示例：

- 原句：`你的 React 组件在重新渲染，原因是每次渲染都创建了新的对象引用，导致 props 变化。`
- `/wenyan`：`每渲染新对象引用，故重渲染。useMemo 包之。`
- `/xizi`：`新引用，故重渲染。useMemo。`

---

## 真实 benchmark（可复现，非自述）

50 条 golden 中文技术问答（React / Python / SQL / A 股），tiktoken o200k 计数：

| 指标 | 数字 |
|---|---|
| 总体省 token | **25.7%**（1296 → 963 token） |
| 分领域 | react 28.1% / python 25.2% / astock 24.5% / sql 23.4% / general 33.6% |
| 语义保真 | 50/50 条 payload / 数字逐字符保留 |
| 阴性对照 | 「乱删字坏压缩器」被抓出（缺 62 个 payload token） |

复现（Python 3.11+，用 uv）：

```bash
uv sync                                  # 一键建环境（装 tiktoken）
uv run python -m eval.compress_bench     # 压缩率 + 能红断言
uv run python -m eval.semantic_eval      # 语义保真 + 阴性对照
```

**诚实说明**：压缩率因句子类型而异——冗余中文能省 35%+（见 `SKILL.md` 示例），术语 / 专名密集的技术短句只能省 20-25%（英文 payload 必须原样保留）。上表是 50 条 golden 集实测，不是全场景天花板。

---

## 安装

```bash
bash install.sh
```

或手动复制 `SKILL.md` 到 harness 的 skills 目录（见 `adapters/`）：支持 **Claude Code / Codex / opencode**。

## 怎么用

装好后，在 agent 里输入：

- `/xizi` 惜字档（默认，成语 + 极限单字）
- `/wenyan` 文言档
- `/heihua` A 股黑话档

或直接说「省 token / 说短点 / 惜字」。

---

## 五铁律（凭什么敢压）

对标 caveman 的 ASD-STE100 受控英语，中文受控压缩法「惜字法」：

1. **一字一意**：双字压单字（现在→今 / 但是→然 / 因为→因）
2. **成语压缩**：长句压四字
3. **意义不丢**：数字、单位、专名、否定词绝不压
4. **payload 原样**：代码 / 命令 / 路径逐字符保留
5. **工具静默**：工具调用参数不压

---

## 对标与差异化

- caveman（10.9 万星）——英文版做不到「中文单字表意」；
- ponytail（15.4 万星）——教会我们「诚实 benchmark + 主动纠正夸大」；
- superpowers（29.5 万星）——教会我们「唯一正文 SKILL.md + 多 harness 薄适配」。

中文 agent 生态（豆包 / Kimi / Qwen / DeepSeek）里没有对应的「中文省 token skill」= 明确空位。

---

## License

MIT
