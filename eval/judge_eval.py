"""LLM-as-judge 整体语义评测（④）。

用 LLM judge 判断「压缩文是否保留原文的全部关键信息」，补确定性保真检查
（semantic_eval 的 payload/数字）覆盖不到的「整体语义 / 核心断言」。

判据（半可复现）：固定 judge 模型（deepseek-chat）+ temperature 0；
结果记录在输出，非确定性来自模型本身，已在 README 诚实说明口径。

用法：python -m eval.judge_eval --n 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

from .compress_bench import load_all

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
CRED_PATH = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
JUDGE_MODEL = "deepseek-chat"


def _load_api_key() -> str:
    """优先环境变量 DEEPSEEK_API_KEY，fallback 到本机 credentials 文件。"""
    env = os.environ.get("DEEPSEEK_API_KEY")
    if env:
        return env
    with open(CRED_PATH, encoding="utf-8") as f:
        creds = f.read()
    m = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", creds)
    if not m:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY（可设环境变量 DEEPSEEK_API_KEY）")
    return m.group(1)


def judge_semantic(answer: str, compressed: str) -> str:
    """让 judge 判断压缩文是否保留原文全部关键信息，返回「是」/「否」。"""
    prompt = (
        "判断「压缩文」是否保留了「原文」的全部关键信息（数字、单位、专名、否定词、核心断言）。\n"
        f"原文：{answer}\n"
        f"压缩文：{compressed}\n"
        "只回答「是」或「否」，不要解释。"
    )
    payload = json.dumps(
        {
            "model": JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4,
            "temperature": 0,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {_load_api_key()}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


def _is_yes(verdict: str) -> bool:
    return verdict.startswith("是")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args(argv)

    items = load_all()
    tasks = items[: args.n]

    yes = 0
    for it in tasks:
        try:
            verdict = judge_semantic(it["answer"], it["compressed"])
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {it['id']}: judge 失败 {type(e).__name__}: {e}")
            continue
        if _is_yes(verdict):
            yes += 1
            print(f"  ✓ {it['id']}: 语义保留")
        else:
            print(f"  ✗ {it['id']}: 语义丢失（judge={verdict}）")

    print(f"\nLLM-judge 语义保留：{yes}/{len(tasks)}（judge={JUDGE_MODEL}）")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
