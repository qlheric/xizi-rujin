# S1「惜字如金」进度台账

> 记录即真相：每 Phase 完成即登记，含验收判据核验结果。

| Phase | 名称 | 状态 | 完成时间 | 验收结果 |
|---|---|---|---|---|
| P0 | 立项与规格 | ✅ 完成 | 2026-10-06 | 目录结构就位；卖点/三档/五铁律定稿于 `00-S1-详细方案.md`；LICENSE(MIT) + README 骨架已建 |
| P1 | 核心 SKILL.md | ✅ 完成 | 2026-10-06 | `SKILL.md` 正文就绪：frontmatter(触发词)+五铁律+三层压缩档+6 组示例；harness 亲验并入 P2 评测门 |
| P2 | 评测门 | ✅ 完成 | 2026-10-06 | 50 条 golden：总体省 25.7%（1296→963 token）；语义保真 50/50；阴性对照坏压缩器被抓出；能红断言绿 |
| P3 | 多 harness 适配 | ✅ 完成 | 2026-10-06 | Claude Code + Codex 亲验通过：`/xizi` 均正确触发压缩、语义/数字/payload 保留 |
| P4 | README + 物料 | ✅ 完成 | 2026-10-06 | 完整 README（真实数字+诚实边界）+ logo（SVG 印章）+ 四套首发文案 |
| P5 | 发布与复盘 | ✅ 完成 | 2026-10-06 | 已 push 到 https://github.com/qlheric/xizi-rujin（main）；中文社区发帖待老大 |

---

## 关键决策记录

- 2026-10-06：垂直任务 = **文言压缩**（老大拍板「按推荐来」）；项目名 = **「惜字如金」**（repo `xizi-rujin`）。
- 2026-10-06：老大新增执行纪律 —— 小项目也分阶段、每步稳定可靠 + 真实用、站在巨人肩上向上跳、不追速度追高星稳定 + 长期可维护（已入热记忆）。
- 2026-10-06：logo 生图坑 —— cogview 生成的「印章」文字错成「中华人民共国万岁」（AI 生图对中文篆书不可靠）；改用 SVG 手绘印章（文字确定、可维护、可改）。
- 2026-10-06：补强（老大拍「有限窗口 c」）——补 proxy 层：确定性压缩器 + 可插拔词典（`xizi/` 包，wenyan/astock 词典，payload 逐字符保护），`/heihua` 从口号落地；14 个单测全绿。

## P2 评测数字（真实实测，2026-10-06）

- 压缩率（tiktoken o200k_base，50 条 golden 集）：**总体 0.7438，省 25.7%**（1296 → 963 token）。
- 分领域：react 28.1% / python 25.2% / astock 24.5% / sql 23.4% / general 33.6%。
- 单条波动 0.6~0.89：术语/专名密集句压缩空间小（诚实披露，非错误）。
- 语义保真：50/50 条 payload/数字逐字符保留；阴性对照「乱删字坏压缩器」被抓住（缺 62 个 payload token）。
- 复现命令：`python -m eval.compress_bench` / `python -m eval.semantic_eval`。

## 环境事实

- Python：uv 管理 CPython 3.12.13（3.14 无 tiktoken wheel）；`tiktoken==0.14.0` 已装可用。
- 可复现：`uv sync` 一键建环境（tiktoken + xizi-rujin 可编辑安装）；`uv run python -m eval.compress_bench` / `semantic_eval` / `unittest discover` 三者均 exit=0（2026-10-06 亲验）。
- git：本地 `main` 分支，首次 commit `901183d`，全部文件已提交；CI `.github/workflows/ci.yml` 就绪。
