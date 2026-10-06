"""F: 判据层——关键信息保真（数字/专名/核心断言，确定性+归一化）
R: code:eval/cli.py（打分调用）+ code:eval/report.py（失败分析取缺失项）
A: python -m eval.cli 间接调用
S: 判据必须确定性；归一化只抹平格式变体（下标/空格/全角），严禁引入 LLM 打分（防自嗨）
"""

from __future__ import annotations

import json
import os
import unicodedata

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
QA_PATH = os.path.join(DATASETS_DIR, "golden_zh_qa.jsonl")


def _normalize(text: str) -> str:
    """归一化格式变体：Unicode 兼容分解（H₂O→H2O、全角→半角）+ 去空格。

    只抹平格式差异，不改变语义——让「答对但格式不同」不误判，「真答错」仍红。
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return text.replace(" ", "").replace("\u3000", "")


def load_qa(path: str = QA_PATH) -> list[dict]:
    """读中文问答 golden 集（jsonl），每行 {id, domain, question, golden, keys}。"""
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def judge(answer: str | None, entry: dict) -> tuple[bool, list[str]]:
    """关键信息保真：归一化后，answer 必须包含 entry['keys'] 的每个 key。

    返回 (是否通过, 缺失的关键信息列表)。确定性、能红、可复现。
    """
    if answer is None:
        answer = ""
    norm_answer = _normalize(answer)
    missing = [k for k in entry.get("keys", []) if _normalize(k) not in norm_answer]
    return (len(missing) == 0), missing
