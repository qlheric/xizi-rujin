"""确定性压缩器（proxy 层核心）。

流程：payload 保护 → 词典替换（长词优先）→ payload 还原。
可复现：同一文本、同一词典，输出确定。
"""

from __future__ import annotations

import re

from .glossary.astock import ASTOCK
from .glossary.cyber import CYBER
from .glossary.gaming import GAMING
from .glossary.gongwen import GONGWEN
from .glossary.internet import INTERNET
from .glossary.medical import MEDICAL
from .glossary.wenyan import WENYAN, XIZI

# payload 保护：反引号代码 / 英文标识符 / 数字百分比 —— 逐字符保留（五铁律 4）
# 用「联合正则 + 一次 sub」：replacement 不会被再次扫描，避免占位符被二次匹配。
_PAYLOAD = re.compile(r"`[^`]+`|[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?%?")

_PLACEHOLDER = "\uE000{}\uE001"

# 压缩档 → 词典（/wenyan /xizi 通用档 + 各领域黑话档）
RULES_BY_LEVEL: dict[str, dict[str, str]] = {
    "wenyan": WENYAN,
    "xizi": XIZI,
    "heihua": ASTOCK,  # 兼容：heihua = A股黑话（SKILL.md 三档之一）
    "astock": ASTOCK,
    "internet": INTERNET,
    "gongwen": GONGWEN,
    "cyber": CYBER,
    "gaming": GAMING,
    "medical": MEDICAL,
}


def _protect(text: str) -> tuple[str, list[str]]:
    """把 payload 替换成占位符，返回 (保护后文本, 片段列表)。"""
    frags: list[str] = []

    def save(m: re.Match) -> str:
        frags.append(m.group(0))
        return _PLACEHOLDER.format(len(frags) - 1)

    text = _PAYLOAD.sub(save, text)
    return text, frags


def _restore(text: str, frags: list[str]) -> str:
    for i, f in enumerate(frags):
        text = text.replace(_PLACEHOLDER.format(i), f)
    return text


def compress(text: str, level: str = "xizi") -> str:
    """确定性压缩。level ∈ {wenyan, xizi, heihua}。"""
    if level not in RULES_BY_LEVEL:
        raise ValueError(
            f"未知压缩档：{level}（可选 wenyan / xizi / heihua / astock / "
            f"internet / gongwen / cyber / gaming / medical）"
        )
    rules = RULES_BY_LEVEL[level]
    protected, frags = _protect(text)
    # 长词优先，避免短词先替换破坏长词
    for phrase in sorted(rules, key=len, reverse=True):
        protected = protected.replace(phrase, rules[phrase])
    return _restore(protected, frags)
