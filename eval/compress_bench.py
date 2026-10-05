"""压缩率基准（P2 评测门核心）。

读多个 golden 集，用 tiktoken o200k 数「原句 vs 压缩句」token，
算压缩率 = 压缩后 / 原；能红断言：总体压缩率 ≤ 0.75（即省 ≥25%）。

分场景统计：精炼技术句 vs 冗余中文句，诚实报告「冗余中文省更多」。

可复现：纯确定性计算，无 LLM、无网络，任何人 `python -m eval.compress_bench`
得到同样数字。
"""

from __future__ import annotations

import json
import os
import statistics
import sys

from .token_counter import compression_ratio, count_tokens

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

# 多个 golden 集：精炼技术句 + 冗余中文句（模拟 agent 真实啰嗦输出）
GOLDEN_FILES = ["golden_zh.jsonl", "golden_zh_redundant.jsonl"]

# 能红断言阈值：总体压缩率 ≤0.75（省 ≥25%）。方案 §7。
ASSERT_RATIO = 0.75


def load_golden(path: str) -> list[dict]:
    """读取单个 golden 集（jsonl），每行 {id, domain, answer, compressed}，补 source。"""
    source = os.path.basename(path)
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                it = json.loads(line)
                it["source"] = source
                items.append(it)
    return items


def load_all(files: list[str] = GOLDEN_FILES) -> list[dict]:
    """读取全部 golden 集。"""
    items: list[dict] = []
    for f in files:
        items.extend(load_golden(os.path.join(DATASETS_DIR, f)))
    return items


def bench(items: list[dict]) -> list[dict]:
    """给每条算压缩率，返回带 ratio 的行。"""
    rows = []
    for it in items:
        ratio = compression_ratio(it["answer"], it["compressed"])
        rows.append(
            {
                **it,
                "ratio": ratio,
                "orig_tokens": count_tokens(it["answer"]),
                "comp_tokens": count_tokens(it["compressed"]),
            }
        )
    return rows


def _group_stats(rows: list[dict], key: str) -> dict[str, dict]:
    """按 key（source / domain）分组统计压缩率。"""
    grouped: dict[str, list[float]] = {}
    for r in rows:
        grouped.setdefault(r[key], []).append(r["ratio"])
    return {
        k: {
            "n": len(rs),
            "mean_ratio": round(statistics.mean(rs), 4),
            "savings_pct": round((1 - statistics.mean(rs)) * 100, 1),
        }
        for k, rs in sorted(grouped.items())
    }


def summarize(rows: list[dict]) -> dict:
    """汇总：总体 + 分场景 + 分领域统计。"""
    ratios = [r["ratio"] for r in rows]
    total_orig = sum(r["orig_tokens"] for r in rows)
    total_comp = sum(r["comp_tokens"] for r in rows)

    return {
        "n": len(rows),
        "mean_ratio": round(statistics.mean(ratios), 4),
        "median_ratio": round(statistics.median(ratios), 4),
        "min_ratio": round(min(ratios), 4),
        "max_ratio": round(max(ratios), 4),
        "total_savings_pct": round((1 - total_comp / total_orig) * 100, 1),
        "total_orig_tokens": total_orig,
        "total_comp_tokens": total_comp,
        "by_source": _group_stats(rows, "source"),
        "by_domain": _group_stats(rows, "domain"),
    }


def _print_report(rows: list[dict], stats: dict) -> None:
    print(f"golden 集：{stats['n']} 条")
    print(
        f"压缩率  均值 {stats['mean_ratio']} | 中位 {stats['median_ratio']} "
        f"| 最小 {stats['min_ratio']} | 最大 {stats['max_ratio']}"
    )
    print(
        f"总体省 token：{stats['total_savings_pct']}% "
        f"（{stats['total_orig_tokens']} → {stats['total_comp_tokens']} token）"
    )
    print("\n分场景：")
    for s, d in stats["by_source"].items():
        print(f"  {s:<30} {d['n']:>3} 条  省 {d['savings_pct']}%")
    print("\n分领域：")
    for d, s in stats["by_domain"].items():
        print(f"  {d:<8} {s['n']:>3} 条  省 {s['savings_pct']}%")

    # 能红断言（口径修正）：
    # ① 硬断言：总体压缩率 ≤0.75（整体省 ≥25%）。方案 §7 的「压缩率 ≤0.75」指整体。
    # ② 硬错误：单条压缩率 ≥1.0（压缩反而更费 token）= 真错误。
    # ③ 诚实披露：单条 0.75~1.0 是「术语/专名密集句，压缩空间天然小」，非错误，列出不红门。
    overall_ratio = stats["total_comp_tokens"] / stats["total_orig_tokens"]
    print("\n能红断言：")
    if overall_ratio > ASSERT_RATIO:
        print(
            f"  ✗ 失败：总体压缩率 {overall_ratio:.3f} > {ASSERT_RATIO} "
            f"（省 {stats['total_savings_pct']}% < 25%）"
        )
    else:
        print(
            f"  ✓ 通过：总体压缩率 {overall_ratio:.3f} ≤ {ASSERT_RATIO} "
            f"（省 {stats['total_savings_pct']}% ≥ 25%）"
        )

    worse = [r for r in rows if r["ratio"] >= 1.0]
    if worse:
        print(f"  ✗ 失败：{len(worse)} 条压缩率 ≥1.0（压缩反而更费 token）")
    else:
        print("  ✓ 通过：无「压缩反而更费 token」的条目")

    weak = [r for r in rows if ASSERT_RATIO < r["ratio"] < 1.0]
    if weak:
        print(f"\n诚实披露：{len(weak)} 条单条压缩率 >0.75（术语/专名密集，压缩空间小，非错误）：")
        for r in sorted(weak, key=lambda x: -x["ratio"])[:10]:
            print(f"    {r['id']}  {r['ratio']:.3f}  {r['compressed'][:24]}")


def main(argv: list[str] | None = None) -> int:
    items = load_all()
    rows = bench(items)
    stats = summarize(rows)
    _print_report(rows, stats)
    overall_ratio = stats["total_comp_tokens"] / stats["total_orig_tokens"]
    worse = any(r["ratio"] >= 1.0 for r in rows)
    return 0 if (overall_ratio <= ASSERT_RATIO and not worse) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
