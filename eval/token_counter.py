"""Token 计数（tiktoken o200k_base，对标 caveman 同口径）。

用途：给「原句 vs 压缩句」数 token，算压缩率。
可复现：同一文本、同一编码，结果确定，任何人可重算。
"""

from __future__ import annotations

import tiktoken

_ENCODING_NAME = "o200k_base"
_encoder: tiktoken.Encoding | None = None


def get_encoder() -> tiktoken.Encoding:
    """返回全局单例 tiktoken 编码器（o200k_base，OpenAI GPT-4o 同款）。"""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(_ENCODING_NAME)
    return _encoder


def count_tokens(text: str) -> int:
    """数一段文本的 token 数。"""
    return len(get_encoder().encode(text))


def compression_ratio(original: str, compressed: str) -> float:
    """压缩率 = 压缩后 token / 原 token。0~1，越小越省。

    返回值 < 1 表示省 token；== 1 表示没省；> 1 表示反而更费。
    """
    orig = count_tokens(original)
    comp = count_tokens(compressed)
    if orig == 0:
        raise ValueError("原文本为空，无法计算压缩率")
    return comp / orig


def savings_pct(original: str, compressed: str) -> float:
    """省 token 百分比（正数=省，负数=更费）。"""
    return (1.0 - compression_ratio(original, compressed)) * 100.0
