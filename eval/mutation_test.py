"""F: 简化变异测试器——AST 变异 + 跑测试 + 变异得分（低分=假绿）
R: code:eval/fake_green.py（同 AST 思路）；SKILL 与 bench 组 4 共用 PASS_THRESHOLD
A: python -m eval.mutation_test <source.py> --cmd "<测试命令>"
S: 基线不绿则无法判定；超时算被杀；字节码缓存不得串味；通过线只有 PASS_THRESHOLD 一处；新算子见 _CMP_SWAPS / _BIN_SWAPS
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

# 唯一通过线。SKILL 的「≥80%」、CLI 退出码、bench 组 4 的放行都读这里，禁止再各写各的。
PASS_THRESHOLD = 0.8
MUTANT_LIMIT = 30  # 最小实现：单文件最多变异体数（控制耗时）
DEFAULT_TIMEOUT = 60


@dataclass
class MutationReport:
    """一次变异测试的结论。score 为 None 表示没法打分（无法判定）。"""

    verdict: str  # 通过 / 打回 / 无法判定
    score: float | None
    killed: int
    total: int
    reason: str


def verdict_from_score(score: float, threshold: float = PASS_THRESHOLD) -> str:
    """得分达到阈值才是「通过」，否则「打回」。"""
    if score >= threshold:
        return "通过"
    return "打回"


def _conclusion(report: MutationReport, threshold: float) -> str:
    """给人看的结论行。0 分那句与 README 演示保持同一句。"""
    if report.verdict == "无法判定":
        return f"结论：无法判定——{report.reason}"
    if report.verdict == "通过":
        return f"结论：通过——变异得分 {report.score:.0%} 达到通过阈值 {threshold:.0%}。"
    if report.killed == 0:
        return "结论：打回——测试抓不住任何 bug，这个「通过」不算数。"
    return (
        f"结论：打回——变异得分 {report.score:.0%} 低于通过阈值 {threshold:.0%}，"
        "这个「通过」不算数。"
    )


# 比较符只换相邻的那一个，外加 == → >=（偶数只测一边时，>= 0 会整段变真）。
_CMP_SWAPS: tuple[tuple[type[ast.cmpop], type[ast.cmpop], str], ...] = (
    (ast.Eq, ast.NotEq, "== → !="),
    (ast.Eq, ast.GtE, "== → >="),
    (ast.NotEq, ast.Eq, "!= → =="),
    (ast.Gt, ast.GtE, "> → >="),
    (ast.GtE, ast.Gt, ">= → >"),
    (ast.Lt, ast.LtE, "< → <="),
    (ast.LtE, ast.Lt, "<= → <"),
)
# 真除同时换成乘和地板除。只测能整除的点会杀掉「/ → *」，但杀不掉「/ → //」。
_BIN_SWAPS: tuple[tuple[type[ast.operator], type[ast.operator], str], ...] = (
    (ast.Add, ast.Sub, "+ → -"),
    (ast.Sub, ast.Add, "- → +"),
    (ast.Mult, ast.Div, "* → /"),
    (ast.Div, ast.Mult, "/ → *"),
    (ast.Div, ast.FloorDiv, "/ → //"),
    (ast.FloorDiv, ast.Div, "// → /"),
)


def _cmp_with(node: ast.Compare, index: int, new_op: ast.cmpop) -> ast.Compare:
    ops = list(node.ops)
    ops[index] = new_op
    return ast.Compare(left=node.left, ops=ops, comparators=list(node.comparators))


def _mutate_node(node: ast.AST) -> list[tuple[ast.AST, str]]:
    """对一个 AST 节点生成变异体。顺序固定，方便复现。"""
    out: list[tuple[ast.AST, str]] = []
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            for old_t, new_t, label in _CMP_SWAPS:
                if isinstance(op, old_t):
                    out.append((
                        _cmp_with(node, i, new_t()),
                        f"line {node.lineno} 比较符 {label}",
                    ))
    elif isinstance(node, ast.BinOp):
        for old_t, new_t, label in _BIN_SWAPS:
            if isinstance(node.op, old_t):
                out.append((
                    ast.BinOp(left=node.left, op=new_t(), right=node.right),
                    f"line {node.lineno} {label}",
                ))
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            out.append((ast.BoolOp(op=ast.Or(), values=list(node.values)),
                        f"line {node.lineno} and → or"))
        elif isinstance(node.op, ast.Or):
            out.append((ast.BoolOp(op=ast.And(), values=list(node.values)),
                        f"line {node.lineno} or → and"))
    elif isinstance(node, ast.Constant):
        if node.value is True:
            out.append((ast.Constant(value=False), f"line {node.lineno} True → False"))
        elif node.value is False:
            out.append((ast.Constant(value=True), f"line {node.lineno} False → True"))
        elif isinstance(node.value, str):
            out.append((ast.Constant(value=node.value + "XX"),
                        f"line {node.lineno} 字符串追加 XX"))
        elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool) and node.value != 0:
            out.append((ast.Constant(value=node.value + 1),
                        f"line {node.lineno} 数字 {node.value} → {node.value + 1}"))
    elif isinstance(node, ast.Return) and node.value is not None:
        out.append((ast.Return(value=ast.Constant(value=None)),
                    f"line {node.lineno} return x → return None"))
        # 只对比较 / 布尔表达式加 return True。数值函数上这是必杀，会把窄测试的得分抬过 80%。
        if isinstance(node.value, (ast.Compare, ast.BoolOp)):
            out.append((ast.Return(value=ast.Constant(value=True)),
                        f"line {node.lineno} return 比较/布尔 → return True"))
    elif isinstance(node, ast.Assign) and not isinstance(node.value, (ast.Constant, ast.Name)):
        out.append((ast.Assign(targets=node.targets, value=ast.Constant(value=None)),
                    f"line {node.lineno} 赋值 → None"))
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and not node.args
        and not node.keywords
    ):
        out.append((node.func.value, f"line {node.lineno} 去掉调用 .{node.func.attr}()"))
    elif isinstance(node, ast.IfExp) and isinstance(node.orelse, ast.Name):
        # 不在这里把条件取反。v2_09 现为 3/4=75%，再加一个必杀变异会变成 4/5=80% 被放行。
        out.append((
            ast.IfExp(test=node.test, body=node.body, orelse=ast.Constant(value=None)),
            f"line {node.lineno} else {node.orelse.id} → None",
        ))
    return out


def _docstring_ids(tree: ast.AST) -> set[int]:
    """模块和函数开头的文档字符串。改它测试通常看不见，算等价变异，不生成。"""
    found: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def generate_mutants(source: str) -> list[tuple[str, str]]:
    """生成变异体列表 [(变异后源码, 描述)]。

    两坑都踩过：①id(node) 跨 parse 不稳定（变异撞错节点）②NodeTransformer 原地改树，
    第一个变异体注入后树被改（Constant 被替换掉），后续变异体找不到目标。
    正解：「行号+列号+类型」定位（跨树稳定）+ 每个变异体用**新 parse 的树**注入。
    """
    base = ast.parse(source)
    skip_doc = _docstring_ids(base)
    spots: list[tuple[tuple[int, int, str], ast.AST, str]] = []
    for node in ast.walk(base):
        if id(node) in skip_doc:
            continue
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
        if mutated == ast.unparse(ast.parse(source)):
            continue  # 换完和原文一样，是空变异
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


def _purge_module_pyc(source_path: str) -> None:
    """删掉这个模块旁边的 .pyc。

    只设 PYTHONDONTWRITEBYTECODE 不够：那个开关不读旧缓存。源文件大小没变、
    mtime 又落在同一秒时，解释器会直接跑上一份字节码。
    """
    directory = os.path.dirname(os.path.abspath(source_path)) or "."
    cache = os.path.join(directory, "__pycache__")
    stem = os.path.splitext(os.path.basename(source_path))[0]
    if not os.path.isdir(cache):
        return
    for name in os.listdir(cache):
        if name.startswith(stem + "."):
            try:
                os.remove(os.path.join(cache, name))
            except OSError:
                pass


def _child_env(cache_root: str) -> dict[str, str]:
    """子进程单独用一份空的缓存目录，并且不再把 .pyc 写回源码树。"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = cache_root
    return env


def _run_cmd(cmd: str, timeout: float, env: dict[str, str], source_path: str) -> tuple[str, int | None]:
    """跑一条测试命令。返回 (ok|fail|timeout, 退出码)。"""
    _purge_module_pyc(source_path)
    run_env = dict(env)
    # 每个变异体换一个空目录，同长度同秒写入也撞不上上一份字节码。
    run_env["PYTHONPYCACHEPREFIX"] = tempfile.mkdtemp(prefix="mut-", dir=env["PYTHONPYCACHEPREFIX"])
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=timeout,
            env=run_env,
        )
    except subprocess.TimeoutExpired:
        return "timeout", None
    if result.returncode == 0:
        return "ok", 0
    return "fail", result.returncode


def _finish(report: MutationReport, threshold: float) -> MutationReport:
    print(_conclusion(report, threshold))
    return report


def run_mutation(
    source_path: str,
    test_cmd: str,
    timeout: float = DEFAULT_TIMEOUT,
    threshold: float | None = None,
) -> MutationReport:
    """变异 → 跑测试 → 结论。基线不绿、没有变异点，都不给「通过」。"""
    if threshold is None:
        threshold = PASS_THRESHOLD
    with open(source_path, encoding="utf-8") as f:
        original = f.read()
    cache_root = tempfile.mkdtemp(prefix="xizi-pyc-")
    env = _child_env(cache_root)
    try:
        status, code = _run_cmd(test_cmd, timeout, env, source_path)
        if status == "timeout":
            return _finish(MutationReport(
                "无法判定", None, 0, 0,
                "基线测试超时。原始测试自己都跑不完，变异得分不能当成通过。",
            ), threshold)
        if status != "ok":
            return _finish(MutationReport(
                "无法判定", None, 0, 0,
                f"基线测试没有通过（退出码 {code}）。测试本来就是红的，或者命令写错，变异得分不能当成通过。",
            ), threshold)

        mutants = generate_mutants(original)
        if not mutants:
            return _finish(MutationReport(
                "无法判定", None, 0, 0,
                "没有找到变异点。没有变异点不等于测试有效。",
            ), threshold)

        killed = 0
        for i, (mutated, desc) in enumerate(mutants):
            try:
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(mutated)
                status, _code = _run_cmd(test_cmd, timeout, env, source_path)
                if status == "timeout":
                    killed += 1
                    print(f"  变异体 {i+1:2d} [{desc}]: 被杀（超时）✓")
                elif status != "ok":
                    killed += 1
                    print(f"  变异体 {i+1:2d} [{desc}]: 被杀 ✓")
                else:
                    print(f"  变异体 {i+1:2d} [{desc}]: 存活——假绿！✗")
            finally:
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(original)
                _purge_module_pyc(source_path)

        score = killed / len(mutants)
        verdict = verdict_from_score(score, threshold)
        print(
            f"\n变异得分：{killed}/{len(mutants)}（{score:.0%}）"
            f"——通过阈值 {threshold:.0%}；被杀=测试真能抓 bug；存活=假绿\n"
        )
        reason = "达到通过阈值" if verdict == "通过" else "低于通过阈值"
        return _finish(MutationReport(verdict, score, killed, len(mutants), reason), threshold)
    finally:
        shutil.rmtree(cache_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="被测源文件（会被临时变异，测后恢复）")
    ap.add_argument("--cmd", required=True, help="测试命令，如 python -m pytest tests/test_x.py")
    ap.add_argument(
        "--threshold",
        type=float,
        default=PASS_THRESHOLD,
        help=f"通过阈值，默认 {PASS_THRESHOLD}（与 SKILL、bench 组 4 同一处）",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="单条测试命令的超时秒数；超时的变异体算被杀，不让整个工具崩掉",
    )
    args = ap.parse_args(argv)
    report = run_mutation(args.source, args.cmd, timeout=args.timeout, threshold=args.threshold)
    if report.verdict == "通过":
        return 0
    if report.verdict == "无法判定":
        return 2
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
