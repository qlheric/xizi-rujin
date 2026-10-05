"""token_counter 单元测试 + SKILL.md 6 示例压缩率冒烟测试。

既是单元测试，也是 P2 的第一次「亲验」：真实 tiktoken 计数，
验证「惜字如金」的 before/after 示例确实省 token（不信声称）。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.token_counter import compression_ratio, count_tokens, savings_pct

# SKILL.md §六 的 6 组示例（before, after）
EXAMPLES: list[tuple[str, str]] = [
    (
        "这个函数的时间复杂度是 O(n²)，因为里面有两层嵌套循环，当数据量很大时会非常慢。",
        "此函数 O(n²)。两层循环，数据大则极慢。",
    ),
    (
        "Python 的字典在 3.7 版本之后保证了插入顺序，所以你可以依赖它的顺序来遍历。",
        "Python 字典自 3.7 起保插入序，可依序遍历。",
    ),
    (
        "这段代码用 useMemo 缓存了计算结果，只有当依赖项 [a, b] 发生变化时才会重新计算。",
        "useMemo 缓存结果，仅依赖 [a, b] 变时重算。",
    ),
    (
        "git rebase 会把你的提交重新应用到目标分支的顶端，和 git merge 不同，它不会产生合并提交。",
        "git rebase 重放提交于目标分支顶端；异于 git merge，不产合并提交。",
    ),
    (
        "报错 TypeError: Cannot read properties of undefined (reading 'map') 说明你在对一个 undefined 值调用 map 方法，需要先检查数据是否已经加载。",
        "Cannot read properties of undefined (reading 'map') → 对 undefined 调 .map。先验数据已载。",
    ),
    (
        "ImportError: No module named 'numpy' 表示 numpy 没有安装，你需要运行 pip install numpy 来安装它。",
        "No module named 'numpy' → numpy 未装。运行 pip install numpy 装之。",
    ),
]


class TestTokenCounter(unittest.TestCase):
    def test_count_empty(self) -> None:
        self.assertEqual(count_tokens(""), 0)

    def test_count_nonempty(self) -> None:
        self.assertGreater(count_tokens("你好，世界"), 0)

    def test_compression_ratio_raises_on_empty_original(self) -> None:
        with self.assertRaises(ValueError):
            compression_ratio("", "x")

    def test_examples_all_save_tokens(self) -> None:
        """6 组示例每一组都必须省 token（压缩率 < 0.9）。"""
        for orig, comp in EXAMPLES:
            ratio = compression_ratio(orig, comp)
            self.assertLess(
                ratio, 0.9, f"应省 token，实际压缩率 {ratio:.3f}：{comp[:20]}"
            )


def _print_report() -> None:
    print(f"{'组':<4}{'原token':>8}{'压token':>8}{'压缩率':>9}{'省%':>8}")
    for i, (orig, comp) in enumerate(EXAMPLES, 1):
        ot = count_tokens(orig)
        ct = count_tokens(comp)
        print(f"{i:<4}{ot:>8}{ct:>8}{ct / ot:>9.3f}{(1 - ct / ot) * 100:>7.1f}%")
    tot_o = sum(count_tokens(o) for o, _ in EXAMPLES)
    tot_c = sum(count_tokens(c) for _, c in EXAMPLES)
    print("-" * 40)
    print(f"合计  {tot_o:>6}{tot_c:>6}{tot_c / tot_o:>9.3f}{(1 - tot_c / tot_o) * 100:>7.1f}%")


if __name__ == "__main__":
    import sys as _sys

    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _print_report()
    print("=" * 40)
    unittest.main(verbosity=2)
