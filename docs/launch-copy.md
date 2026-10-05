# 首发文案（四套渠道）

> P4 物料。发布时按渠道取用；数字均来自 P2 真实评测（省 25.7%）。

## 即刻（短梗，社区感）

中文自带一个 token 压缩器，叫「文言文」。

为什么用一堆 token？一个汉字就够了。

惜字如金 —— 教你的 coding agent 说人话更省。
实测省 25.7% token，代码 / 命令 / 数字一个不丢。
对标 caveman（10.9w⭐），这是中文版。

## X（中英混合，国际化）

why use many token when one Chinese character do trick 🪨→🀄

惜字如金 (xizi-rujin): a meme skill that makes your coding agent speak 文言 / 成语 / 黑话, cutting Chinese prompt tokens by 25.7% — measured with tiktoken, not claimed.

/caveman but for Chinese. 中文版 caveman。

## 掘金（技术向，深度）

给中文 LLM 场景做了个「省 token」的 skill：惜字如金。

对标 caveman 的 ASD-STE100 受控英语，我把中文的压缩方法学成了「五铁律」：一字一意 / 成语压缩 / 意义不丢 / payload 原样 / 工具静默。

50 条 golden 集（React/Python/SQL/A股）tiktoken o200k 实测：总体省 25.7%，payload 逐字符保留，能红断言 + 阴性对照全绿。

诚实 benchmark 的部分：术语密集句只能省 20-25%（英文 payload 必须原样），冗余中文能省 35%+。不吹天花板，报实测中位数。

## V2EX（理性技术）

分享一个开源小项目：惜字如金（xizi-rujin），中文版「省 token」skill。

对标 caveman（10.9w star），用文言 / 成语 / 黑话压缩中文输出。
tiktoken o200k 实测 50 条 golden 集省 25.7%，代码 / 命令 / 数字逐字符保留。
可复现：`python -m eval.compress_bench`，数字任何人能重算。

诚实的部分：压缩率随句子冗余度波动（20%～35%+），不是一刀切 50%。
支持 Claude Code / Codex / opencode，MIT。
