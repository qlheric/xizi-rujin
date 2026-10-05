"""语义保留评测（P2 评测门）—— 验证「省 token 不以丢意义为代价」。

两层（先确定性，后 LLM-judge 可选）：
1. 确定性保真检查（可核、能红）：payload（英文标识符/代码/命令）与数字
   必须逐字符保留 —— 五铁律 3、4 的机器验证。
2. 阴性对照：内置「乱删字」坏压缩器，保真检查必须抓出它（证明断言能红）。

可复现：确定性检查无 LLM、无网络；`python -m eval.semantic_eval` 得同样结果。
"""

from __future__ import annotations

import json
import os
import re
import sys

from .token_counter import count_tokens

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "datasets", "golden_zh.jsonl")

# 英文标识符（代码/命令/API 名）：大小写敏感，逐字符保留。
_EN_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
# 数字 + 可选百分比（五铁律 3：数字绝不压缩）。
_NUM = re.compile(r"\d+(?:\.\d+)?%?")


def load_golden(path: str = GOLDEN_PATH) -> list[dict]:
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def extract_payload(text: str) -> list[str]:
    """提取需逐字符保留的 token：英文标识符 + 数字/百分比。"""
    tokens: list[str] = []
    tokens.extend(m.group() for m in _EN_IDENT.finditer(text))
    tokens.extend(m.group() for m in _NUM.finditer(text))
    return tokens


def check_fidelity(answer: str, compressed: str) -> list[str]:
    """返回 compressed 中缺失的 payload token 列表（空 = 保真通过）。"""
    return [t for t in extract_payload(answer) if t not in compressed]


def bad_compressor(text: str) -> str:
    """阴性对照：乱删字坏压缩器 —— 删光英文与数字，必然破坏意义。"""
    return re.sub(r"[A-Za-z0-9_./+\-%]+", "", text)


def main(argv: list[str] | None = None) -> int:
    items = load_golden()
    print(f"语义保真检查：golden 集 {len(items)} 条\n")

    total_missing = 0
    for it in items:
        missing = check_fidelity(it["answer"], it["compressed"])
        total_missing += len(missing)
        if missing:
            print(f"  ✗ {it['id']}: 缺失 payload {missing}")

    print("\n能红断言（确定性保真）：")
    ok = True
    if total_missing == 0:
        print(f"  ✓ 通过：{len(items)} 条 compressed 均保留原 payload/数字")
    else:
        print(f"  ✗ 失败：共缺失 {total_missing} 个 payload/数字 token")
        ok = False

    # 阴性对照：坏压缩器必须被抓住
    print("\n阴性对照（坏压缩器必须被抓出）：")
    bad_missing_total = 0
    for it in items:
        bad = bad_compressor(it["answer"])
        bad_missing_total += len(check_fidelity(it["answer"], bad))
    if bad_missing_total > 0:
        print(f"  ✓ 通过：坏压缩器被抓住，缺失 {bad_missing_total} 个 payload token")
    else:
        print("  ✗ 失败：坏压缩器未被抓住（保真检查失效）")
        ok = False

    print(f"\n参考：坏压缩器只省 token 但丢意义 —— 见下例")
    example = items[0]
    bad = bad_compressor(example["answer"])
    print(f"  原: {example['answer']}")
    print(f"  坏: {bad}  (token {count_tokens(example['answer'])}→{count_tokens(bad)})")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
