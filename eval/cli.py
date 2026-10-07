"""F: 评测入口——mock agent 自检（零网络可复现）+ 真实 LLM 评测（--engine）
R: code:eval/judge.py + eval/assertions.py + eval/report.py + eval/datasets/golden_zh_qa.jsonl
A: python -m eval.cli（mock 自检）；python -m eval.cli --engine deepseek|claude|gpt（真实评测）
S: mock 必须零网络（阴性对照可复现）；真实 LLM 用 temperature=0（可复现）；结果严禁回写 golden
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request

from .assertions import run_assertions
from .judge import judge, load_qa
from .report import report

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
CLAUDE_URL = "https://4sapi.org/v1/chat/completions"
GPT_URL = "https://4sapi.com/v1/chat/completions"
QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
CRED_PATH = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")

# 禁用代理直连：本机 IE 代理设置指向已关闭的代理端口时，urllib 会读它导致 ConnectionRefused。
# 实测 deepseek / dashscope（国内）与 4sapi 直连均通，统一直连。
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _load_key(name: str) -> str:
    env = os.environ.get(name)
    if env:
        return env
    with open(CRED_PATH, encoding="utf-8") as f:
        creds = f.read()
    m = re.search(rf"{name}:\s*(\S+)", creds)
    if not m:
        raise RuntimeError(f"未找到 {name}（可设环境变量 {name}）")
    return m.group(1)


def run_agent(engine: str, question: str) -> str:
    """调真实 LLM 回答 question，返回答案文本。temperature=0 保可复现。"""
    if engine == "deepseek":
        url, model, key = DEEPSEEK_URL, "deepseek-chat", _load_key("DEEPSEEK_API_KEY")
        payload = {"model": model, "messages": [{"role": "user", "content": question}], "max_tokens": 2000, "temperature": 0}
    elif engine == "claude":
        url, model, key = CLAUDE_URL, "claude-opus-5-5", _load_key("S4API_CLAUDE_API_KEY")
        payload = {"model": model, "messages": [{"role": "user", "content": question}], "max_tokens": 2000, "temperature": 0}
    elif engine == "gpt":
        url, model, key = GPT_URL, "gpt-6-astra", _load_key("S4API_API_KEY")
        # 推理模型：推理阶段耗 token，max_completion_tokens 要给足（实测 200 会空答）
        payload = {"model": model, "messages": [{"role": "user", "content": question}], "max_completion_tokens": 4000, "temperature": 0}
    elif engine == "qwen":
        url, model, key = QWEN_URL, "qwen-turbo", _load_key("BAILIANAPIKEY")
        # 详细解题型模型：max_tokens 要给足（实测 200 会截断在解题过程、写不到最终答案）
        payload = {"model": model, "messages": [{"role": "user", "content": question}], "max_tokens": 2000, "temperature": 0}
    else:
        raise ValueError(f"未知引擎：{engine}")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    # gpt（4sapi.com）需走系统代理（直连超时）；deepseek/dashscope/4sapi.org 直连
    opener = urllib.request.urlopen if engine == "gpt" else _NO_PROXY_OPENER.open
    last: Exception | None = None
    for _ in range(3):  # 重试 3 次，抗网络波动（RemoteDisconnected/URLError）
        try:
            with opener(req, timeout=120) as r:
                resp = json.loads(r.read())
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise last  # type: ignore[misc]


def mock_good(entry: dict) -> str:
    return entry["golden"]


def mock_bad(entry: dict) -> str:
    return ""


def llm_review(question: str, golden: str, answer: str, missing_keys: list[str], engine: str = "deepseek") -> bool:
    """LLM-judge 复核同义变体：返回 True=同义等价（撤销失败），False=确实缺失（保留）。

    只复核「文本同义」，不宽恕「数字/事实错误」——数字必须精确一致（23 不等于 32、也不等于 12）。
    """
    if not (answer or "").strip():
        return False  # 空答案不可能语义等价
    prompt = (
        f"agent 的回答被判「缺失关键信息：{missing_keys}」。请判断这些关键信息是真的缺失，还是以等价形式出现了。\n"
        f"硬规则：数字必须精确一致（23 不等于 32，也不等于 12）；只有同义措辞才算等价（找不到=未找到、公里=千米）；"
        f"只有最终答案里的关键信息才算数，解题过程/公式推导不算。\n"
        f"问题：{question}\n"
        f"标准答案：{golden}\n"
        f"agent 回答：{answer}\n"
        f"只回答「等价」或「缺失」。"
    )
    verdict = run_agent(engine, prompt).strip()
    return verdict.startswith("等价")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=None, choices=["deepseek", "claude", "gpt", "qwen"],
                    help="接真实 LLM 评测；省略则 mock 自检（零网络）")
    ap.add_argument("--n", type=int, default=50, help="跑前 n 条 golden")
    ap.add_argument("--review", action="store_true",
                    help="对失败案例用 LLM-judge 复核同义变体（辅助，结果公开）")
    args = ap.parse_args(argv)

    entries = load_qa()[: args.n]

    if args.engine is None:
        # mock 自检：好 agent=golden、必错 agent=空答，零网络验证闭环
        good = [(e, mock_good(e), *judge(mock_good(e), e)) for e in entries]
        bad = [(e, mock_bad(e), *judge(mock_bad(e), e)) for e in entries]
        good_pass = sum(1 for r in good if r[2])
        bad_pass = sum(1 for r in bad if r[2])
        ok = run_assertions(good_pass, bad_pass, len(entries))
        print(f"\n=== 好 agent（mock=golden）报告 ===")
        report(entries, good)
        print(f"\n=== 必错 agent（mock=空答，阴性对照）报告 ===")
        report(entries, bad)
        return 0 if ok else 1

    # 真实 LLM 评测
    print(f"评测引擎：{args.engine}（temperature=0）\n")
    results = []
    for e in entries:
        try:
            ans = run_agent(args.engine, e["question"])
        except Exception as exc:  # noqa: BLE001
            ans = ""
            print(f"  ✗ {e['id']}: 调用失败 {type(exc).__name__}")
        passed, missing = judge(ans, e)
        results.append((e, ans, passed, missing))

    good_pass = sum(1 for r in results if r[2])

    # LLM-judge 复核（可选）：对确定性判据的失败案例复核同义变体（直接改 results）
    if args.review:
        fails = [r for r in results if not r[2]]
        if fails:
            print(f"\n=== LLM-judge 复核（{len(fails)} 条失败案例，同义变体检查）===")
            for idx, (entry, ans, _passed, missing) in enumerate(results):
                if _passed:
                    continue
                try:
                    ok_syn = llm_review(entry["question"], entry["golden"], ans, missing)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ? {entry['id']}: 复核调用失败 {type(exc).__name__}（保留失败）")
                    continue
                if ok_syn:
                    results[idx] = (entry, ans, True, missing)
                    print(f"  ↻ {entry['id']}: 语义等价，撤销失败（判据误判：{missing}）")
                else:
                    print(f"  ✗ {entry['id']}: 复核确认答错（{missing}）")
        good_pass = sum(1 for r in results if r[2])

    # 阴性对照（mock 必错 agent，零网络）
    bad = [(e, mock_bad(e), *judge(mock_bad(e), e)) for e in entries]
    bad_pass = sum(1 for r in bad if r[2])
    ok = run_assertions(good_pass, bad_pass, len(entries))

    print(f"\n=== 被测 agent（{args.engine}）报告 ===")
    report(entries, results)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
