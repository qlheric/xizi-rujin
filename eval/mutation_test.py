"""F: 简化变异测试器——AST 变异 + 跑测试 + 变异得分（低分=假绿，阶段 2 硬工具）
R: code:eval/fake_green.py（同 AST 思路）；阶段 3 SKILL 调用本模块
A: python -m eval.mutation_test <source.py> --cmd "<测试命令>"
S: 变异用标准库 ast（零外部依赖，替代 mutmut 的 libcst）；「替换源文件→跑测试→恢复」必须 finally 保证恢复；变异得分=被杀/总数
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys

MUTANT_LIMIT = 30  # 最小实现：单文件最多变异体数（控制耗时）


def _mutate_node(node: ast.AST) -> list[tuple[ast.AST, str]]:
    """对一个 AST 节点生成变异体列表 [(变异体AST, 描述)]。核心 8 算子。"""
    out: list[tuple[ast.AST, str]] = []
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            new = None
            if isinstance(op, ast.Eq):
                new = ast.NotEq()
            elif isinstance(op, ast.Gt):
                new = ast.GtE()
            if new is not None:
                ops = list(node.ops)
                ops[i] = new
                out.append((ast.Compare(left=node.left, ops=ops, comparators=node.comparators),
                            f"line {node.lineno} 比较符 {ast.dump(op)}→{ast.dump(new)}"))
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        out.append((ast.BinOp(left=node.left, op=ast.Sub(), right=node.right),
                    f"line {node.lineno} + → -"))
    elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        out.append((ast.BoolOp(op=ast.Or(), values=node.values),
                    f"line {node.lineno} and → or"))
    elif isinstance(node, ast.Constant):
        if node.value is True:
            out.append((ast.Constant(value=False), f"line {node.lineno} True → False"))
        elif node.value is False:
            out.append((ast.Constant(value=True), f"line {node.lineno} False → True"))
        elif isinstance(node.value, (int, float)) and node.value != 0:
            out.append((ast.Constant(value=node.value + 1), f"line {node.lineno} 数字 {node.value} → {node.value + 1}"))
    elif isinstance(node, ast.Return) and node.value is not None:
        out.append((ast.Return(value=ast.Constant(value=None)),
                    f"line {node.lineno} return x → return None"))
    elif isinstance(node, ast.Assign) and not isinstance(node.value, (ast.Constant, ast.Name)):
        out.append((ast.Assign(targets=node.targets, value=ast.Constant(value=None)),
                    f"line {node.lineno} 赋值 → None"))
    return out


def generate_mutants(source: str) -> list[tuple[str, str]]:
    """生成变异体列表 [(变异后源码, 描述)]。

    两坑都踩过：①id(node) 跨 parse 不稳定（变异撞错节点）②NodeTransformer 原地改树，
    第一个变异体注入后树被改（Constant 被替换掉），后续变异体找不到目标。
    正解：「行号+列号+类型」定位（跨树稳定）+ 每个变异体用**新 parse 的树**注入。
    """
    base = ast.parse(source)
    spots: list[tuple[tuple[int, int, str], ast.AST, str]] = []
    for node in ast.walk(base):
        for m, desc in _mutate_node(node):
            key = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0), type(node).__name__)
            spots.append((key, m, desc))
    mutants: list[tuple[str, str]] = []
    for key, m, desc in spots:
        tree = ast.parse(source)  # 每次新树，防原地修改污染
        injector = _Injector(key, m)
        try:
            mutated = ast.unparse(injector.visit(tree))
        except Exception:
            continue  # 变异产生非法语法则跳过该变异体
        mutants.append((mutated, desc))
        if len(mutants) >= MUTANT_LIMIT:
            break
    return mutants


class _Injector(ast.NodeTransformer):
    """把指定「位置+类型」的节点替换成变异体。"""

    def __init__(self, key: tuple[int, int, str], replacement: ast.AST):
        self.key = key
        self.replacement = replacement

    def visit(self, node):  # noqa: D102
        key = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0), type(node).__name__)
        if key == self.key:
            return self.replacement
        return super().visit(node)


def run_mutation(source_path: str, test_cmd: str) -> float:
    """核心：变异 → 跑测试 → 变异得分。返回被杀比例。"""
    with open(source_path, encoding="utf-8") as f:
        original = f.read()
    mutants = generate_mutants(original)
    if not mutants:
        print("没有找到变异点。")
        return 1.0

    killed = 0
    for i, (mutated, desc) in enumerate(mutants):
        try:
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(mutated)
            result = subprocess.run(test_cmd, shell=True, capture_output=True, timeout=60)
            if result.returncode != 0:
                killed += 1
                print(f"  变异体 {i+1:2d} [{desc}]: 被杀 ✓")
            else:
                print(f"  变异体 {i+1:2d} [{desc}]: 存活——假绿！✗")
        finally:
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(original)  # 无条件恢复原文件

    score = killed / len(mutants)
    print(f"\n变异得分：{killed}/{len(mutants)}（{score:.0%}）——被杀=测试真能抓 bug；存活=假绿")
    return score


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="被测源文件（会被临时变异，测后恢复）")
    ap.add_argument("--cmd", required=True, help="测试命令，如 python -m pytest tests/test_x.py")
    args = ap.parse_args(argv)
    score = run_mutation(args.source, args.cmd)
    return 0 if score >= 0.5 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
