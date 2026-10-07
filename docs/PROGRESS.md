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
- 2026-10-06：补强 ② —— 扩充冗余中文 golden 集（13 条）+ 端到端评测（claude 9/10 保真）；分场景省 token：冗余中文 62.4% vs 精炼技术句 25.6%，总体 37.9%；端到端抓出真实边界「JavaScript→JS 专名缩写」。
- 2026-10-06：补强 ③④ —— tokenizer 双轨（o200k 37.9% / cl100k 43.2%，验证稳健）+ LLM-judge 整体语义（judge=deepseek-chat，10/10 保留）。
- 2026-10-06：补强 ⑤（领域拓展，老大拍「不止 A股、多领域」）——词典从 A股 扩到 6 领域（A股金融 50+ / 互联网 30+ / 公文 40+ / 网络梗 30+ / 电竞 30+ / 医疗 30+，共 200+ 词条）；修 cli.py 档位集硬编码 bug（改为自动同步）；16 单测全绿 + CLI 六路冒烟通过。
- 2026-10-06：补强 ⑥（领域再拓，老大拍「越多越好、供用户选择」）——词典扩到 13 领域（新增二次元/恋爱/职场/饭圈/学术/粤语/美食），400+ 词条；报错信息改为动态生成；23 单测全绿 + CLI 十三路冒烟通过。
- 2026-10-06：补强 ⑦（长尾拓展，老大拍「继续完善」）——词典扩到 23 领域（新增法律/健身/摄影/宠物/汽车/母婴/房产/数码/体育/美妆），600+ 词条；29 单测全绿 + CLI 二十三路冒烟通过。
- 2026-10-06：放大器（老大拍「先做放大器」）——写技术深度文 `docs/article.md`（方法学 + 诚实 benchmark + 23 领域），供知乎/掘金发布。
- 2026-10-06：放大器（续）——调研 awesome 收录目标（4 个列表 + GitHub topics），清单落 `docs/awesome-submission.md`；提交 PR 待 qlheric 账号。
- 2026-10-06：放大器执行 —— 发帖 X + 掘金（即刻/V2EX 有注册门槛，暂缓）；awesome PR 提交 2 个（travisvn/awesome-claude-skills 表格行 + VoltAgent/awesome-agent-skills 的 Context Engineering 区），待 maintainer review。
- 2026-10-06：真实使用案例（老大拍「做真实使用案例」）——stock-tool 真实话术做「黑话 vs 白话」对比（省 39~51%），案例落 `docs/case-study.md`；**只读 stock-tool、未碰任何生产代码**。
- 2026-10-06：S1 收口（老大拍「本会话只 S1 + 后续维护」）——后续维护 = 盯 2 个 awesome PR（travisvn/awesome-claude-skills + VoltAgent/awesome-agent-skills）review 状态，有评论即改；PR 号待老大补。
- 2026-10-06：S1 再转型（老大拍「转 ponytail 式规则」→ 交叉评审否掉「反过度规则复刻经营」→ 收敛「中文 agent 可信评测」）——可信评测最小闭环完成：golden 50 条 + judge（关键信息保真+归一化）+ assertions（阴性对照）+ report（失败分析）+ cli（mock/真实LLM/复核）；三模型实测 deepseek 100% / claude 96% / gpt 100%；沉淀 keys 设计原则（核心且不可同义替换）+ 归一化（H₂O→H2O）+ LLM-judge 复核（同义变体）。
- 2026-10-06：名字保持「惜字如金」（老大拍「中文博大精深」）——新诠释：不只省字，更是对每个字较真（可信评测的严谨）。
- 2026-10-06：可信评测扩量（老大拍「扩量 + 弱模型」）——golden 50→150（easy 50/medium 50/hard 50，借鉴 C-Eval 分层 + CMMLU 中国特有主题），新增领域 gongwu/economy/law/idiom/math；报告加按难度/领域分层；deepseek 150 条 146/150（97%），弱项 math 8/10、gongwu 11/12、tech 29/30。
- 2026-10-06：三模型 150 条对比 —— deepseek 97% / gpt 93% / claude 84%；run_agent 加 3 次重试（抗网络波动）；claude 出现「easy 42/50 反而低于 hard 46/50」的推理模型行为差异（可信评测抓出的真实现象）。
- 2026-10-06：弱模型对照（老大提供百炼 key BAILIANAPIKEY）——qwen-turbo 150 条 99%，**它不是弱模型**（中文问答+计算强）；修三处真问题：复核洗白数字（严格 prompt：数字精确+解题过程不算）、max_tokens 截断详细解题（200→2000）、urllib 读 IE 死代理（改直连 _NO_PROXY_OPENER）；归一化加去千分位逗号。
- 2026-10-06：真难题 50 条（hardplus：行测数量/逻辑/高考数学，老大拍「加」）——总量 200（easy/medium/hard/hardplus 各 50）；deepseek 200 条 98%（hardplus 46/50）vs qwen 96%（hardplus 45/50），区分度仍小（两个中文模型都强）；gpt/claude 200 条后台补跑中。
- 2026-10-06：B 收尾 —— 四模型 hardplus：gpt 49/50（98%）、claude 48/50（96%）、deepseek 46/50（92%）、qwen 45/50（90%）；全程又修 4 处：medium 28 条 keys 违规（题目术语不在 golden，mock 假象被"满分断言"戳穿）、LaTeX 归一化（frac/boxed/pi）、gpt 渠道走代理分路（4sapi.com 直连超时）、hp048 出题错误（1.25×0.8=1 抵消，改打 9 折）；诚实结论：四强模型都在 96~98% 高分段，真分层需压轴题难度。
- 2026-10-07：方向再评审（老大问「方向真的对吗」→ 换模型评审「质检员人格」）——两模型共识：收窄定位到「拦截假绿」（agent 说"搞定/通过"时拦截）、薄人格+硬工具（变异测试/静态检测）、benchmark 测错误放行率四组对照、口号「没红过的绿，都是假绿」；老大拍「按修正方向分阶段升级，每阶段最小实现停一下验收」。
- 2026-10-07：升级阶段 1 完成（假绿静态检测器 `eval/fake_green.py`，老大验收通过）——6 类作弊模式（assert True/False、skip/xfail、except pass 吞异常、无断言、assertEqual 同源）；真实 tests 验收抓出 2 误报（unittest self.assertXxx、防御性 except）+ 1 真弱断言（test_all_domains_registered）并修复；最终 0 误报 + 29 单测回归绿。
- 2026-10-07：升级阶段 2 完成（简化变异测试器 `eval/mutation_test.py`，老大验收通过）——标准库 ast 零依赖 8 算子（==→!=、>→>=、+→-、and→or、True↔False、数字+1、return→None、赋值→None）+ 变异得分；真红验证：好测试 3/3 杀（100%）vs 假绿 assert True 0/3 存活（0%），源文件 finally 恢复；踩坑：id(node) 跨 parse 不稳定（变异撞错 def 参数）→ 同树注入；pwsh 引号嵌套传错 cmd → 验证方式修正。
- 2026-10-07：升级阶段 3 完成（老审计人格 `SKILL.md`，等老大验收）——三句口头禅（红过吗/错的抓得住吗/挂的那些呢）+ 三态输出（通过/有条件通过/打回）+ 证据强制（没命令+输出摘录不许写已验证）+ 分寸三档（快检/抽检/全检）+ 硬工具接线（fake_green/mutation_test）；claude 实测触发：面对"测试全过了"声称 → 核查发现测试不存在 → 判打回（真实拦截演示）。
- 2026-10-07：阶段 3 权威优化（老大验收意见「人格是否足够权威」）——权威从"自称"改为"有出处"：三问锚定 TDD 红绿循环（Kent Beck）+ 变异测试（Lipton 1971/DeMillo 1978）+ 审计准则「反向证据」「工作底稿」（司法部审计准则）；权威三层=人格→方法论出处→审计证据链；claude 实测面对"你凭什么审我"直接跑证据回答；顺带修复现命令改 uv run（裸 python 缺 tiktoken）。
- 2026-10-07：升级阶段 4 完成（假绿陷阱集 10 个 + 四组对照 `eval/bench.py`，等老大验收）——四组数据：组1 原始 LLM 0/10、组2 认真检查 0/10、组3 老审计 0/10、组4 工具链 3/10 放行；诚实结论：陷阱对 deepseek 太简单（明显假绿一眼看穿，四组分不出差别）+ 组4 漏的 3 个是「硬编码错误期望」（变异测试原理盲区：oracle 错了测不出）；设计教训：陷阱 bug 注释=泄题（已去）；待拍：陷阱集 v2（更难）还是进阶段 5。
- 2026-10-07：陷阱集 v2（老大拍「做 v2」）+ 四组对照真区分——v2 陷阱=「测试只覆盖一个分支/路径，未覆盖分支变异存活」；关键发现：deepseek 本身就会审计（组1-3 全 0%），换 qwen 弱模型才分出差别：qwen 组1 100% 轻信 vs 组2 认真检查 30% vs 组3 老审计 0% vs 组4 工具链 40%；归因结论：价值主要来自方法论三问（100%→0%），工具链价值=确定性证据而非独立判定（40% 盲区：硬编码期望+变异点落在被测路径）；顺带修 mutation_test 深坑：NodeTransformer 原地改树污染后续变异体 → 改「位置定位+每次新树」。
- 2026-10-07：升级阶段 5 完成（假绿灯档案 + README 重构，老大验收通过，「拦截假绿」升级收口）——`docs/fake-green-archive.md` 6 篇真实案例（LLM 复核洗白/max_tokens 截断/IE 死代理/keys 违规/真弱断言/出题错误），每篇四件事（原来为何通过/漏了什么/什么暴露/怎么修）+ 总教训（假绿五形态）；README 按「拦截假绿」重构：第一屏假绿灯演示 + 三问出处 + 硬工具 + 四组对照数据 + 诚实盲区；**5 阶段全部完成**。
- 2026-10-07：对外物料更新（定位从省 token 变拦截假绿）——2 个 awesome PR 的 README 行已改成「fake-green interceptor」新描述（亲验 patch 确认）；PR 标题还是旧的（travisvn #1302「Add xizi-rujin skill to README」/ VoltAgent #1164「Chinese token compression」）待老大改；repo About 描述待改；仓库名拍「暂不改」（惜字如金=对每个字较真的新诠释还搭得上，GitHub rename 有 301 重定向以后可改）。
- 2026-10-07：对外物料全部更新完成（亲验四样）——PR 标题 ×2 改「Add xizi-rujin — fake-green interceptor skill (老审计)」✓、repo About 改「老审计·拦截假绿」✓、qlheric Profile README 改「专治一种病：AI 说成功了其实没有」✓、PR README 行 ✓；仓库名暂不改（老大默认）。

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
