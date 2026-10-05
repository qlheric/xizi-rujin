"""Token 计数（tiktoken，多编码双轨）。

主口径 o200k_base（GPT-4o，对标 caveman）；参考口径 cl100k_base（GPT-3.5/4）。
双轨用于验证压缩率稳健：不同 tokenizer 口径下「省 token」结论一致。

可复现：同一文本、同一编码，结果确定，任何人可重算。
"""

from __future__ import annotations

import tiktoken

ENCODINGS = ["o200k_base", "cl100k_base"]
DEFAULT_ENCODING = "o200k_base"

_encoders: dict[str, tiktoken.Encoding] = {}


def get_encoder(name: str = DEFAULT_ENCODING) -> tiktoken.Encoding:
    """返回 tiktoken 编码器（按名缓存）。"""
    if name not in _encoders:
        _encoders[name] = tiktoken.get_encoding(name)
    return _encoders[name]


def count_tokens(text: str, encoding: str = DEFAULT_ENCODING) -> int:
    """数一段文本的 token 数（指定编码口径）。"""
    return len(get_encoder(encoding).encode(text))


def compression_ratio(
    original: str, compressed: str, encoding: str = DEFAULT_ENCODING
) -> float:
    """压缩率 = 压缩后 token / 原 token。0~1，越小越省。"""
    orig = count_tokens(original, encoding)
    comp = count_tokens(compressed, encoding)
    if orig == 0:
        raise ValueError("原文本为空，无法计算压缩率")
    return comp / orig


def savings_pct(
    original: str, compressed: str, encoding: str = DEFAULT_ENCODING
) -> float:
    """省 token 百分比（正数=省，负数=更费）。"""
    return (1.0 - compression_ratio(original, compressed, encoding)) * 100.0
