# 惜字如金 · xizi-rujin

<p align="center"><img src="assets/logo.svg" width="160" alt="惜字如金 logo"></p>

> *why use many token when one Chinese character do trick*

**中文版「省 token」meme skill** —— 教 coding agent 用「文言 / 成语 / 黑话」说话，把 prompt 的 token 砍掉一大截。

中文单字表意、四字成语、垂直黑话，是中文自带的压缩基因。caveman / ponytail 的英文版做不到。

---

## 两层架构（对标 caveman）

| 层 | 实现 | 作用 |
|---|---|---|
| **人格层** | `SKILL.md` | 教 agent 用文言思维压缩输出（灵活，覆盖词典外） |
| **机制层** | `xizi/` 确定性压缩器 | 词典 + 规则确定性压缩（可复现、免费、词典可插拔） |

---

## 三层压缩档

| 档 | 命令 | 风格 | 压缩率 |
|---|---|---|---|
| 文言档 | `/wenyan` | 文言文（之乎者也 + 单字） | 中 |
| 惜字档 | `/xizi` | 成语 + 极限单字 | 高 |
| 黑话档 | `/heihua` | A 股 / 垂直术语缩写 | 最高（领域化） |

示例（`SKILL.md` 人格层输出）：

- 原句：`你的 React 组件在重新渲染，原因是每次渲染都创建了新的对象引用，导致 props 变化。`
- `/wenyan`：`每渲染新对象引用，故重渲染。useMemo 包之。`
- `/xizi`：`新引用，故重渲染。useMemo。`

---

## 真实 benchmark（可复现，非自述）

63 条 golden 中文（React / Python / SQL / A 股），tiktoken o200k 计数：

| 指标 | 数字 |
|---|---|
| 总体省 token | **37.9%**（o200k） / 43.2%（cl100k）双轨 |
| 分场景 | 冗余中文 **62.4%** / 精炼技术句 25.6% |
| 语义保真 | 63/63 条 payload / 数字逐字符保留 |
| LLM-judge 整体语义 | 10/10 保留（judge=deepseek-chat） |
| 端到端（真实 agent） | 9/10 保真（claude `/xizi` 压缩后 payload 不丢） |
| 阴性对照 | 「乱删字坏压缩器」被抓出（缺 76 个 payload token） |

复现（Python 3.11+，用 uv）：

```bash
uv sync                                  # 一键建环境（装 tiktoken）
uv run python -m eval.compress_bench     # 压缩率 + 能红断言
uv run python -m eval.semantic_eval      # 语义保真 + 阴性对照
uv run python -m eval.judge_eval         # LLM-judge 整体语义（需 DEEPSEEK_API_KEY）
```

**诚实说明**：①压缩率因句子类型而异——冗余中文（模拟 agent 真实啰嗦输出）省 62.4%，术语 / 专名密集的精炼技术句只省 25.6%（英文 payload 必须原样保留）。②tokenizer 口径影响绝对数字（o200k 37.9% / cl100k 43.2%），但「显著省 token」的结论稳健。③端到端 9/10 的 1 个失败是「JavaScript 缩成 JS」这类专名缩写（真实 agent 也会犯），正是五铁律「专名不丢」要防的边界。数字是 golden 集实测，不是全场景天花板。

---

## 安装

```bash
uv sync            # Python 依赖（tiktoken + xizi 包）
bash install.sh    # 把 SKILL.md 装到 Claude Code / Codex / opencode
```

## 使用

**方式一：agent 里装 skill** —— 装好后在 agent 里输入 `/xizi` / `/wenyan` / `/heihua`，或说「省 token / 说短点 / 惜字」。

**方式二：CLI 直接压缩**（确定性、可复现、payload 保护）：

```bash
python -m xizi.cli xizi "因为现在可以处理这个问题，所以需要修改代码"
# 因今可理此题，故需改代码

python -m xizi.cli heihua "在股价低位时买入"
# 抄底
```

三层档：`wenyan`（单字）/ `xizi`（单字 + 短语）/ `heihua`（A 股黑话）。

**方式三：领域黑话档**（白话 → 领域高密度术语，中文独有、英文无法复刻）：

```bash
python -m xizi.cli astock "市盈率"          # PE
python -m xizi.cli internet "关键绩效指标"   # KPI
python -m xizi.cli gongwen "深入贯彻落实"    # 落实
python -m xizi.cli cyber "永远的神"          # yyds
python -m xizi.cli gaming "远程物理输出核心"  # ADC
python -m xizi.cli medical "急性心肌梗死"     # 心梗
```

| 档 | 领域 | 示例 |
|---|---|---|
| `wenyan` / `xizi` | 通用文言 / 成语 | 因为→因 / 现在→今 |
| `astock` / `heihua` | A股金融黑话 | 市盈率→PE / 止损卖出→割肉 |
| `internet` | 互联网大厂黑话 | 关键绩效指标→KPI |
| `gongwen` | 体制内公文 | 深入贯彻落实→落实 |
| `cyber` | 网络流行语 | 永远的神→yyds |
| `gaming` | 游戏电竞 | 远程物理输出核心→ADC |
| `medical` | 医疗术语 | 急性心肌梗死→心梗 |
| `acg` | 二次元 / ACG | 动画剧集→番 |
| `romance` | 恋爱 / 情感 | 心动对象→crush |
| `workplace` | 职场 | 被公司辞退→毕业 |
| `fandom` | 饭圈 / 追星 | 偶像塌房→塌房 |
| `academic` | 学术 / 考研 | 考研成功上岸→上岸 |
| `cantonese` | 粤语 / 方言 | 没有→冇 |
| `food` | 美食 / 餐饮 | 吃饭→干饭 |
| `legal` | 法律 | 依法追究刑事责任→追刑责 |
| `fitness` | 健身 / 运动 | 力量训练→撸铁 |
| `photography` | 摄影 / 摄像 | 感光度→ISO |
| `pet` | 宠物 | 养猫的铲屎官→铲屎官 |
| `auto` | 汽车 | 涡轮增压发动机→涡轮 |
| `parenting` | 母婴 / 育儿 | 母乳喂养→母乳 |
| `realestate` | 房产 / 租房 | 住房公积金贷款→公积金贷 |
| `tech` | 数码 / 科技 | 中央处理器→处理器 |
| `sports` | 体育 / 球类 | 帽子戏法→帽子戏法 |
| `beauty` | 美妆 / 护肤 | 敏感性皮肤→敏感肌 |

可插拔词典：`xizi/glossary/` 下每个文件是一个领域词典，共 23 领域 600+ 词条；加新领域只需加一个文件、不改核心逻辑。

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
