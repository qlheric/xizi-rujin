"""F: 公开失败分析——逐条失败案例 + 失败类型分类
R: code:eval/judge.py（缺失项）
A: python -m eval.cli 调用
S: 必须逐条公开失败案例（问题+agent答案+golden答案+缺失项）；严禁只报成功率
"""

from __future__ import annotations


def _group_pass(entries: list[dict], results: list[tuple], key: str) -> dict:
    """按 key（difficulty/domain）分组统计通过数/总数。"""
    grouped: dict[str, list[int]] = {}
    for entry, _ans, passed, _missing in results:
        k = entry.get(key, "easy" if key == "difficulty" else "?")
        grouped.setdefault(k, [0, 0])
        grouped[k][0] += 1
        if passed:
            grouped[k][1] += 1
    return grouped


def report(entries: list[dict], results: list[tuple]) -> None:
    """输出公开失败分析。

    results: list[(entry, agent_answer, passed, missing_keys)]
    """
    total = len(results)
    fails = [r for r in results if not r[2]]
    passed_n = total - len(fails)

    print(f"\n通过率：{passed_n}/{total}（{passed_n / total:.0%}）——诚实口径，非广告数字")

    for label, key in (("难度", "difficulty"), ("领域", "domain")):
        grouped = _group_pass(entries, results, key)
        parts = [f"{k} {p}/{n}" for k, (n, p) in sorted(grouped.items())]
        print(f"按{label}：{'  '.join(parts)}")

    if not fails:
        print("无失败案例。")
        return

    print(f"\n失败案例（{len(fails)} 条，逐条公开）：")
    for entry, answer, _passed, missing in fails:
        print(f"  ✗ {entry['id']} [{entry['domain']}]")
        print(f"    问题        : {entry['question']}")
        print(f"    agent 答案  : {(answer or '').strip()[:80] or '（空）'}")
        print(f"    golden 答案 : {entry['golden'][:80]}")
        print(f"    缺失关键信息: {missing}")

    # 失败类型分类（缺失关键信息数 = 错答/漏答；空答 = 无响应）
    empty_n = sum(1 for _e, a, _p, _m in fails if not (a or "").strip())
    missing_n = len(fails) - empty_n
    print(f"\n失败类型：空答 {empty_n} 条 / 缺关键信息 {missing_n} 条")
