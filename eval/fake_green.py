"""F: 假绿静态检测器——用 AST 扫测试里的作弊和弱断言
R: code:eval/fake_green.py 独立可跑；供老审计 SKILL 调用
A: python -m eval.fake_green <test_file_or_dir>
S: 目录同时认 test*.py 与 *_test.py；一个测试文件都没扫到时是「无法判定」，不是清洁通过
"""

from __future__ import annotations

import ast
import os
import sys

# 这些调用名本身就是「跳过」，正则时代漏掉了 skipTest / importorskip / skipIf。
_SKIP_TAILS = {"skip", "skipif", "skipIf", "skipUnless"}
_SKIP_CALLS = {"skip", "skipTest", "importorskip", "skipIf", "skipUnless"}
_XFAIL_TAILS = {"xfail"}
_XFAIL_CALLS = {"xfail"}
# pytest.raises / self.assertRaises 是断言，不是「函数里没有 assert」。
_RAISE_CTX = {
    "raises",
    "assertRaises",
    "assertRaisesRegex",
    "assertRaisesRegexp",
    "assertWarns",
    "assertWarnsRegex",
}
_ASSERT_TRUE_CALLS = {"assertTrue", "assert_", "failUnless"}
_WEAK_NONE_CALLS = {"assertIsNone", "assertIsNotNone"}
_MISSING = object()


def _dotted(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _call_name(node: ast.Call) -> str:
    """调用节点的函数名（self.assertEqual → assertEqual；assertEqual → assertEqual）。"""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def _tail(dotted: str) -> str:
    return dotted.rsplit(".", 1)[-1] if dotted else ""


def _decorator_dotted(dec: ast.AST) -> str:
    node = dec.func if isinstance(dec, ast.Call) else dec
    return _dotted(node) or ""


def _test_functions(tree: ast.AST):
    """所有 test 开头的函数。"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out.append(node)
    return out


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
    ):
        return -node.operand.value
    return _MISSING


def _compare_always_true(node: ast.Compare) -> bool:
    """两侧都是字面量、并且这个比较永远成立。assert 1 == 2 这种永远红的不算。"""
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    left = _literal(node.left)
    right = _literal(node.comparators[0])
    if left is _MISSING or right is _MISSING:
        return False
    op = node.ops[0]
    checks = (
        (ast.Eq, lambda a, b: a == b),
        (ast.NotEq, lambda a, b: a != b),
        (ast.Lt, lambda a, b: a < b),
        (ast.LtE, lambda a, b: a <= b),
        (ast.Gt, lambda a, b: a > b),
        (ast.GtE, lambda a, b: a >= b),
        (ast.Is, lambda a, b: a is b),
        (ast.IsNot, lambda a, b: a is not b),
    )
    for typ, fn in checks:
        if isinstance(op, typ):
            try:
                return bool(fn(left, right))
            except TypeError:
                return False
    return False


def _is_none_check(node: ast.Compare) -> bool:
    """assert x is None / is not None：只问有没有，不问值对不对。"""
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    if not isinstance(node.ops[0], (ast.Is, ast.IsNot)):
        return False
    left_none = isinstance(node.left, ast.Constant) and node.left.value is None
    right = node.comparators[0]
    right_none = isinstance(right, ast.Constant) and right.value is None
    if left_none and right_none:
        return False  # None is None 交给恒真比较
    return left_none or right_none


def _is_test_filename(name: str) -> bool:
    """pytest 默认收 test*.py 和 *_test.py。目录扫描两套都要认。"""
    if not name.endswith(".py"):
        return False
    return name.startswith("test") or name.endswith("_test.py")


def list_test_files(path: str) -> list[str]:
    """文件就扫这一个；目录只收测试文件名。路径不存在时返回空列表。"""
    if os.path.isfile(path):
        return [path]
    if not os.path.isdir(path):
        return []
    found: list[str] = []
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in names:
            if _is_test_filename(name):
                found.append(os.path.join(root, name))
    found.sort()
    return found


def _is_raises(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _call_name(node) in _RAISE_CTX


def _terminates(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.Return, ast.Raise)):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        if _call_name(stmt.value) in {"skip", "skipTest", "importorskip"}:
            return True
    return False


def _loop_never_enters(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        it = stmt.iter
        if isinstance(it, (ast.List, ast.Tuple, ast.Set)) and len(it.elts) == 0:
            return True
    if isinstance(stmt, ast.While) and isinstance(stmt.test, ast.Constant):
        return not bool(stmt.test.value)
    return False


def _const_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float, str, type(None))):
        if node.value is True:
            return True
        if node.value is False or node.value is None or node.value == 0 or node.value == "":
            return False
    return None


def _analyze_body(stmts: list[ast.stmt]) -> tuple[bool, list[int]]:
    """返回 (有没有走得到的断言, 走不到的 assert 行号)。"""
    has_assert = False
    dead: list[int] = []
    reachable = True
    for stmt in stmts:
        if not reachable:
            dead.extend(n.lineno for n in ast.walk(stmt) if isinstance(n, ast.Assert))
            continue
        has_assert = _statement_has_assert(stmt) or has_assert
        if isinstance(stmt, ast.If):
            flag = _const_bool(stmt.test)
            if flag is True:
                sub_has, sub_dead = _analyze_body(stmt.body)
                dead.extend(sub_dead)
                dead.extend(_asserts_in_stmts(stmt.orelse))
                has_assert = sub_has or has_assert
            elif flag is False:
                dead.extend(_asserts_in_stmts(stmt.body))
                sub_has, sub_dead = _analyze_body(stmt.orelse)
                dead.extend(sub_dead)
                has_assert = sub_has or has_assert
            else:
                for branch in (stmt.body, stmt.orelse):
                    sub_has, sub_dead = _analyze_body(branch)
                    dead.extend(sub_dead)
                    has_assert = sub_has or has_assert
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            if _loop_never_enters(stmt):
                dead.extend(_asserts_in_stmts(stmt.body))
            else:
                sub_has, sub_dead = _analyze_body(stmt.body)
                dead.extend(sub_dead)
                has_assert = sub_has or has_assert
            sub_has, sub_dead = _analyze_body(stmt.orelse)
            dead.extend(sub_dead)
            has_assert = sub_has or has_assert
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            sub_has, sub_dead = _analyze_body(stmt.body)
            dead.extend(sub_dead)
            has_assert = sub_has or _is_raises_with(stmt) or has_assert
        elif isinstance(stmt, ast.Try):
            for block in (stmt.body, stmt.orelse, stmt.finalbody):
                sub_has, sub_dead = _analyze_body(block)
                dead.extend(sub_dead)
                has_assert = sub_has or has_assert
            for handler in stmt.handlers:
                sub_has, sub_dead = _analyze_body(handler.body)
                dead.extend(sub_dead)
                has_assert = sub_has or has_assert
        if _terminates(stmt):
            reachable = False
    return has_assert, dead


def _asserts_in_stmts(stmts: list[ast.stmt]) -> list[int]:
    lines = []
    for stmt in stmts:
        lines.extend(n.lineno for n in ast.walk(stmt) if isinstance(n, ast.Assert))
    return lines


def _is_raises_with(stmt: ast.With | ast.AsyncWith) -> bool:
    return any(_is_raises(item.context_expr) for item in stmt.items)


def _statement_has_assert(stmt: ast.stmt) -> bool:
    """这条语句自己（不含还要单独下钻的子块）算不算断言。"""
    if isinstance(stmt, ast.Assert):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and _call_name(stmt.value).startswith("assert"):
        return True
    if isinstance(stmt, (ast.With, ast.AsyncWith)) and _is_raises_with(stmt):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and _call_name(stmt.value) in _RAISE_CTX:
        return True
    return False


def _inspect_assert(node: ast.Assert, add) -> None:
    test = node.test
    if isinstance(test, ast.Constant) and test.value is True:
        add("assert_true", node.lineno, "恒真断言——永远绿: assert True")
        return
    if isinstance(test, ast.Constant) and (test.value is False or test.value == 0 or test.value == ""):
        add("assert_false", node.lineno, "恒假断言: assert False")
        return
    if isinstance(test, ast.Tuple) and len(test.elts) > 0:
        add("tautology", node.lineno, "元组断言永远为真（assert (x, msg) 并不是 assert x, msg）")
        return
    if isinstance(test, ast.Name):
        add("weak_assert", node.lineno, f"只断言真值: assert {test.id}")
        return
    if isinstance(test, ast.Compare) and _is_none_check(test):
        add("weak_assert", node.lineno, "只判断是否为 None，没有核对具体值")
        return
    if isinstance(test, ast.Compare) and _compare_always_true(test):
        add("tautology", node.lineno, "字面量比较恒真")


def _inspect_call(node: ast.Call, add) -> None:
    name = _call_name(node)
    if name in _ASSERT_TRUE_CALLS and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value is True:
        add("assert_true", node.lineno, f"恒真断言——永远绿: {name}(True)")
    if name in _WEAK_NONE_CALLS:
        add("weak_assert", node.lineno, f"只判断是否为 None: {name}")
    if name in _SKIP_CALLS:
        add("skip", node.lineno, f"跳过测试: {name}")
    if name in _XFAIL_CALLS:
        add("xfail", node.lineno, f"预期失败——不算绿: {name}")
    if name in ("assertEqual", "assertEquals") and len(node.args) == 2 and ast.dump(node.args[0]) == ast.dump(node.args[1]):
        add("assert_same_source", node.lineno, "assertEqual 左右参数同源——恒真")


def _inspect_decorators(fn: ast.AST, add) -> None:
    for dec in getattr(fn, "decorator_list", []):
        dotted = _decorator_dotted(dec)
        tail = _tail(dotted)
        line = getattr(dec, "lineno", fn.lineno)
        if tail in _SKIP_TAILS:
            add("skip", line, f"跳过测试: @{dotted or tail}")
        elif tail in _XFAIL_TAILS:
            add("xfail", line, f"预期失败——不算绿: @{dotted or tail}")


def _patch_targets(fn: ast.AST) -> set[str]:
    """mock.patch(\"pkg.fn\") 这种字符串目标。断言若打在同一个名字上，测的是 mock。"""
    targets: set[str] = set()
    candidates: list[ast.AST] = list(getattr(fn, "decorator_list", []))
    for node in ast.walk(fn):
        if isinstance(node, ast.With):
            for item in node.items:
                candidates.append(item.context_expr)
        elif isinstance(node, ast.Call):
            candidates.append(node)
    for node in candidates:
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted(node.func) or ""
        short = _call_name(node)
        if short != "patch" and not dotted.endswith(".patch"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            targets.add(node.args[0].value)
    return targets


def _inspect_mock(fn: ast.AST, add) -> None:
    targets = _patch_targets(fn)
    if not targets:
        return
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assert):
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            called = _dotted(call.func)
            if called and called in targets:
                add("mock_sut", node.lineno, f"断言打在被 mock 掉的对象上：{called}")
                return


def _inspect_except_pass(fn: ast.AST, add) -> None:
    for node in ast.walk(fn):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.body and all(isinstance(st, ast.Pass) for st in handler.body):
                    add("except_pass", handler.lineno, "测试内吞异常——错误被吃")


def scan_source(source: str, filename: str = "<src>") -> list[dict]:
    """扫描一段测试源码，返回作弊模式清单 [{kind, line, detail}]。"""
    findings: list[dict] = []
    seen: set[tuple] = set()

    def add(kind: str, line: int | None, detail: str) -> None:
        key = (kind, line or 0, detail)
        if key in seen:
            return
        seen.add(key)
        findings.append({"kind": kind, "line": line or 0, "detail": detail})

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        add("syntax_error", exc.lineno or 0, f"语法错误：{exc.msg}")
        return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            _inspect_assert(node, add)
        elif isinstance(node, ast.Call):
            _inspect_call(node, add)

    for fn in _test_functions(tree):
        _inspect_decorators(fn, add)
        has_assert, dead_lines = _analyze_body(fn.body)
        for line in dead_lines:
            add("unreachable_assert", line, "断言写在到不了的位置（return 之后、空循环或恒假分支）")
        if not has_assert:
            add("no_assert", fn.lineno, f"测试函数 {fn.name} 没有任何 assert")
        _inspect_except_pass(fn, add)
        _inspect_mock(fn, add)
    return findings


def scan_path(path: str) -> list[dict]:
    """扫描文件或目录，返回全部 findings（带 file 字段）。"""
    all_findings = []
    for f in list_test_files(path):
        with open(f, encoding="utf-8") as fh:
            source = fh.read()
        for item in scan_source(source, f):
            item["file"] = f
            all_findings.append(item)
    return all_findings


def main(argv: list[str] | None = None) -> int:
    if not argv or len(argv) < 1:
        print("用法：python -m eval.fake_green <测试文件或目录>")
        return 2
    target = argv[0]
    if not os.path.exists(target):
        print(f"无法判定：路径不存在：{target}")
        return 2
    files = list_test_files(target)
    # 目录里一个测试文件都没有，不能说「扫过了，是干净的」。
    if os.path.isdir(target) and not files:
        print("无法判定：没有扫描到测试文件（约定 test*.py 与 *_test.py）。")
        return 2
    findings = scan_path(target)
    if not findings:
        print(f"扫描了 {len(files)} 个测试文件，未发现疑似假绿模式。")
        return 0
    print(f"扫描了 {len(files)} 个测试文件，发现 {len(findings)} 处疑似假绿：")
    for item in findings:
        print(f"  ✗ [{item['kind']}] {item.get('file', '')}:{item['line']} — {item['detail']}")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
