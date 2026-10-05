"""端到端评测：真实 agent 用 /xizi 压缩 N 个任务，验证「压缩后 payload 不丢」。

对标 caveman 的「54 次 Claude Code runs，18/18 答对」。
判据（确定性、可复现）：agent 压缩输出保留原文的 payload（数字 / 英文标识符）。

用法：
  python -m eval.e2e --engine claude --n 10
  python -m eval.e2e --engine codex --n 10
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from .compress_bench import load_all
from .semantic_eval import check_fidelity


def run_agent(engine: str, prompt: str) -> str:
    """调 harness 非交互跑，返回 stdout 文本。"""
    if engine == "claude":
        cmd = f'claude -p "{prompt}"'
    elif engine == "codex":
        cmd = f'codex exec --skip-git-repo-check -m gpt-6-astra "{prompt}"'
    else:
        raise ValueError(f"未知 engine：{engine}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", timeout=180)
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="claude", choices=["claude", "codex"])
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args(argv)

    items = load_all()
    tasks = items[: args.n]

    passed = 0
    for it in tasks:
        prompt = f"用 /xizi 惜字档压缩这句话（只输出压缩结果，不要解释）：{it['answer']}"
        try:
            out = run_agent(args.engine, prompt)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {it['id']}: 运行失败 {type(e).__name__}")
            continue
        missing = check_fidelity(it["answer"], out)
        if not missing:
            passed += 1
            print(f"  ✓ {it['id']}: 保真  {out[:44]}")
        else:
            print(f"  ✗ {it['id']}: 缺失 payload {missing[:5]}  {out[:44]}")

    print(f"\n端到端保真：{passed}/{len(tasks)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
