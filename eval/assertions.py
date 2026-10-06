"""F: 能红断言——阴性对照证明评测有区分度（必错 agent 必须被判显著差）
R: code:eval/judge.py（打分）
A: python -m eval.cli 调用
S: 核心断言=好agent通过率 − 必错agent通过率 ≥ 60%；不达标则门红（评测是摆设）
"""

from __future__ import annotations

MARGIN = 0.6  # 区分度下限：好 agent 与必错 agent 的通过率差必须 ≥ 60%


def run_assertions(good_pass: int, bad_pass: int, total: int) -> bool:
    """能红断言（阴性对照）：good 通过率必须显著高于 bad。

    返回 True=断言绿；False=门红（评测无区分度）。
    """
    good_rate = good_pass / total if total else 0.0
    bad_rate = bad_pass / total if total else 0.0
    margin = good_rate - bad_rate

    print("\n能红断言（阴性对照）：")
    if margin >= MARGIN:
        print(
            f"  ✓ 通过：好 agent {good_rate:.0%} vs 必错 agent {bad_rate:.0%}，"
            f"区分度 {margin:.0%} ≥ {MARGIN:.0%}"
        )
        return True
    print(
        f"  ✗ 失败：区分度 {margin:.0%} < {MARGIN:.0%}——评测分不出好坏，是摆设"
    )
    return False
