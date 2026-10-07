# 变异测试调研笔记（阶段 2 准备）

> 出处：[mutmut 源码](https://github.com/boxed/mutmut)（`src/mutmut/mutation/mutators.py`，libcst 实现）+ [Stryker 文档](https://stryker-mutator.io/docs/) + [软件学报·变异测试](https://www.jos.org.cn/jos/article/html/4749)。
> 结论：简化版用**标准库 ast** 替代 libcst（零外部依赖），核心算子取 8 个。

## mutmut 的算子清单（完整）

| 算子 | 行为 |
|---|---|
| operator_number | 数字 +1 |
| operator_string | 字符串加 XX / 大小写 |
| operator_name | `True`↔`False`、`deepcopy`→`copy` |
| operator_assignment | 赋值 → `None` |
| operator_augmented_assignment | `+=` → `=` |
| operator_remove_unary_ops | 删一元运算 |
| operator_swap_op | 核心映射 30+ 个（见下） |
| operator_arg_removal | 删函数参数 |
| operator_match / if_exp | 删 match case / 三元条件中和 |

## 核心映射（operator_swap_op，原样摘录要点）

```
== → !=   != → ==   > → >=   >= → >   < → <=   <= → <
+ → -     - → +     * → /     / → *    and → or   or → and
```

## 简化版设计（阶段 2，标准库 ast）

**算子（8 个）**：`==`→`!=`、`>`→`>=`、`+`→`-`、`and`→`or`、`True`→`False`、数字+1、删 return、赋值→`None`。

**流程**：ast.parse 找变异点 → 每个变异点生成变异体（ast 变换 + ast.unparse 回源码）→ subprocess 跑测试（失败=杀、通过=存活）→ 变异得分 = 被杀/总数。

**判据**：变异得分低 = 测试抓不住 bug = 假绿。这是「拦截假绿」的硬证据。
