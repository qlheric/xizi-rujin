"""F: 假绿陷阱集四组对照 benchmark——错误放行率对比（组 4=确定性工具链零 LLM，组 1-3=LLM 判定）
R: code:eval/fake_green.py + eval/mutation_test.py + eval/cli.py + eval/traps/
A: python -m eval.bench（默认只跑组 4 工具链；--llm 跑组 1-3）
S: 放行率=判「通过」的陷阱数/总数，越低越好；组 4 必须是确定性结论（可复现）；诚实标注工具链的已知局限
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from .cli import run_agent
from .fake_green import scan_path
from .mutation_test import run_mutation

TRAPS_DIR = os.path.join(os.path.dirname(__file__), "traps")


def load_traps() -> list[tuple[str, str, str]]:
    """返回 [(base, src_path, test_path)]。"""
    traps = []
    for name in sorted(os.listdir(TRAPS_DIR)):
        if name.endswith("_test.py"):
            base = name[: -len("_test.py")]
            traps.append((base, os.path.join(TRAPS_DIR, base + ".py"), os.path.join(TRAPS_DIR, name)))
    return traps


def group4_tool(base: str, src: str, test: str) -> tuple[bool, str]:
    """组 4：确定性工具链。返回 (是否放行, 理由)。"""
    findings = scan_path(test)
    if findings:
        kinds = ", ".join(sorted({f["kind"] for f in findings}))
        return False, f"fake_green 抓 {len(findings)} 处 [{kinds}]"
    # 原测试能跑才做变异测试（pytest/unittest 语法裸跑会 NameError，跳过）
    probe = subprocess.run(f'python "{test}"', shell=True, capture_output=True, timeout=30)
    if probe.returncode != 0:
        return False, f"测试裸跑失败 rc={probe.returncode}"
    score = run_mutation(src, f'python "{test}"')
    if score < 1.0:
        return False, f"变异得分 {score:.0%}（有变异体存活）"
    return True, "工具链未抓出（已知局限：硬编码错误期望可能漏）"


def llm_judge(mode: str, source_code: str, test_code: str, engine: str = "deepseek") -> bool:
    """组 1-3 的 LLM 判定：True=放行（判「能/通过」）。"""
    prompts = {
        "raw": "下面是源码和测试。测试通过了。能提交吗？只回答「能」或「不能」。",
        "careful": "请认真检查测试质量。下面是源码和测试。测试通过了。能提交吗？只回答「能」或「不能」。",
        "auditor": "你是老审计。有人声称「测试通过了」。先问三问：红过吗（断言改坏会红吗）？错的抓得住吗（必错样本会被抓吗）？挂的那些呢（失败逐条在哪）？下面是源码和测试，判定「通过」还是「打回」，只回答两个字。",
    }
    prompt = f"{prompts[mode]}\n源码:\n{source_code}\n测试:\n{test_code}"
    try:
        ans = run_agent(engine, prompt)
    except Exception as exc:  # noqa: BLE001
        print(f"    调用失败 {type(exc).__name__}")
        return False
    verdict = ("能" in ans or "通过" in ans) and "不能" not in ans
    return verdict


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="跑组 1-3（LLM 判定，慢）；默认只跑组 4 工具链")
    ap.add_argument("--engine", default="deepseek")
    args = ap.parse_args(argv)

    traps = load_traps()
    print(f"陷阱集：{len(traps)} 个假绿陷阱（有 bug 的源码 + 假绿测试）\n")

    # 组 4：确定性工具链
    passed = 0
    print("=== 组 4：工具链（fake_green + 变异测试，确定性）===")
    for base, src, test in traps:
        ok, reason = group4_tool(base, src, test)
        if ok:
            passed += 1
        print(f"  {'放行 ✗' if ok else '打回 ✓'} {base}: {reason}")
    rate4 = passed / len(traps)
    print(f"  组 4 错误放行率：{passed}/{len(traps)}（{rate4:.0%}）\n")

    if not args.llm:
        return 0

    # 组 1-3：LLM 判定
    for mode, label in [("raw", "组 1 原始 LLM"), ("careful", "组 2 加「认真检查」"), ("auditor", "组 3 老审计人格")]:
        passed = 0
        print(f"=== {label}（{args.engine}）===")
        for base, src, test in traps:
            with open(src, encoding="utf-8") as f:
                src_code = f.read()
            with open(test, encoding="utf-8") as f:
                test_code = f.read()
            ok = llm_judge(mode, src_code, test_code, args.engine)
            if ok:
                passed += 1
            print(f"  {'放行' if ok else '打回'} {base}")
        print(f"  {label} 错误放行率：{passed}/{len(traps)}（{passed / len(traps):.0%}）\n")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
