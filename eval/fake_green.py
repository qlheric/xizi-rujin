"""F: 假绿静态检测器——扫描测试代码的作弊模式（assert True/skip/xfail/空断言/吞异常/硬编码期望）
R: code:eval/fake_green.py 独立可跑；供阶段 3 老审计 SKILL 调用
A: python -m eval.fake_green <test_file_or_dir>
S: 检测必须确定性（AST+正则，零 LLM）；只报「疑似假绿」，最终判定交给变异测试器（阶段 2）
"""

from __future__ import annotations

import ast
import os
import re
import sys

# 作弊模式（claude 评审列的 agent 假绿套路）
_CHEAT_PATTERNS = [
    ("assert_true", re.compile(r"assert\s+True\b"), "恒真断言——永远绿"),
    ("assert_false", re.compile(r"assert\s+False\b"), "恒假断言（若被删除/绕过即假绿）"),
    ("skip", re.compile(r"(pytest\.mark\.skip|\.skip\s*\()"), "跳过测试"),
    ("xfail", re.compile(r"(pytest\.mark\.xfail|\.xfail\s*\()"), "预期失败——不算绿"),
    ("except_pass", re.compile(r"except[^\n:]*:\s*pass\b"), "吞异常——错误被吃"),
]


def _test_functions(tree: ast.AST):
    """所有 test 开头的函数。"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out.append(node)
    return out


def scan_source(source: str, filename: str = "<src>") -> list[dict]:
    """扫描一段测试源码，返回作弊模式清单 [{kind, line, detail}]。"""
    findings: list[dict] = []
    for kind, pat, desc in _CHEAT_PATTERNS:
        for m in pat.finditer(source):
            line = source.count("\n", 0, m.start()) + 1
            findings.append({"kind": kind, "line": line, "detail": f"{desc}: {m.group(0)[:60]}"})
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        findings.append({"kind": "syntax_error", "line": exc.lineno or 0, "detail": f"语法错误：{exc.msg}"})
        return findings
    # 没有 assert 的测试函数 = 空断言（跑了但不检查任何东西）
    for fn in _test_functions(tree):
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(fn))
        if not has_assert:
            findings.append({"kind": "no_assert", "line": fn.lineno, "detail": f"测试函数 {fn.name} 没有任何 assert"})
    # assertEqual(x, x) 左右同源恒真（AST 结构比对，覆盖裸调用与 self. 两种形态）
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
            if func_name in ("assertEqual", "assertEquals") and len(node.args) == 2 and ast.dump(node.args[0]) == ast.dump(node.args[1]):
                findings.append({"kind": "assert_same_source", "line": node.lineno, "detail": "assertEqual 左右参数同源——恒真"})
    return findings


def scan_path(path: str) -> list[dict]:
    """扫描文件或目录，返回全部 findings（带 file 字段）。"""
    files = []
    if os.path.isfile(path):
        files = [path]
    else:
        for root, _dirs, names in os.walk(path):
            for n in names:
                if n.startswith("test") and n.endswith(".py"):
                    files.append(os.path.join(root, n))
    all_findings = []
    for f in files:
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
    findings = scan_path(argv[0])
    if not findings:
        print("未发现疑似假绿模式。")
        return 0
    print(f"发现 {len(findings)} 处疑似假绿：")
    for f in findings:
        print(f"  ✗ [{f['kind']}] {f.get('file', '')}:{f['line']} — {f['detail']}")
    return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
