# 首发文案（四套渠道）

> P4 物料，随项目更新。当前数字：总体省 37.9%（o200k）/ 43.2%（cl100k），冗余中文 62.4%，端到端 9/10，LLM-judge 10/10，23 领域词典。
> ⚠️ 数字变了记得同步这里 + README + Profile README + 仓库 Description。

## 即刻（短梗，社区感）

中文自带一个 token 压缩器，叫「文言文」。

为什么用一堆 token？一个汉字就够了。

惜字如金 —— 教你的 coding agent 说人话更省。
实测省 37.9% token，代码 / 命令 / 数字一个不丢。
23 个领域黑话词典（A股 / 二次元 / 饭圈 / 职场…），对标 caveman 的中文版。

## X（中英混合，国际化）

why use many token when one Chinese character do trick 🪨→🀄

惜字如金 (xizi-rujin): a meme skill that makes your coding agent speak 文言 / 成语 / 23-domain jargon, cutting Chinese prompt tokens by 37.9% — tiktoken measured, not claimed. Payload verbatim, 9/10 end-to-end fidelity.

/caveman but for Chinese. 中文版 caveman。

## 掘金（技术向，深度）

给中文 LLM 场景做了个「省 token」的 skill：惜字如金。

对标 caveman 的 ASD-STE100，我把中文的压缩方法学成了「五铁律」：一字一意 / 成语压缩 / 意义不丢 / payload 原样 / 工具静默。

实测（tiktoken o200k）：总体省 37.9%，冗余中文能省 62.4%；双轨 cl100k 省 43.2%；端到端 9/10 保真；LLM-judge 10/10 语义保留。
可复现：`uv sync` + `python -m eval.compress_bench`，数字任何人能重算。

诚实 benchmark：术语密集句只省 25.6%，不吹天花板。23 个领域黑话词典，从 A股到二次元。

## V2EX（理性技术）

分享一个开源小项目：惜字如金（xizi-rujin），中文版「省 token」skill。

对标 caveman（10.9w star），用文言 / 成语 / 23 领域黑话压缩中文输出。
tiktoken o200k 实测 63 条 golden 集总体省 37.9%，代码 / 命令 / 数字逐字符保留。
可复现：`python -m eval.compress_bench`，数字任何人能重算。

诚实的部分：压缩率随句子冗余度波动（25.6%~62.4%），不是一刀切 50%。
支持 Claude Code / Codex / opencode，MIT。
