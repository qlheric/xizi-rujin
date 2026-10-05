"""确定性压缩器单元测试 + payload 保护 + 三档可用。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xizi.compressor import compress


class TestCompressor(unittest.TestCase):
    def test_xizi_saves_tokens(self) -> None:
        """惜字档应把双字压成单字。"""
        out = compress("因为现在可以处理这个问题", "xizi")
        self.assertEqual(out, "因今可理此题")

    def test_wenyan_saves_tokens(self) -> None:
        out = compress("因为现在可以处理这个问题", "wenyan")
        self.assertEqual(out, "因今可理此题")

    def test_payload_protected(self) -> None:
        """代码、数字、英文必须逐字符保留。"""
        text = "用 useMemo 缓存结果，仅依赖 [a, b] 变时重算"
        out = compress(text, "xizi")
        self.assertIn("useMemo", out)
        self.assertIn("[a, b]", out)

    def test_numbers_protected(self) -> None:
        """数字（如版本号 3.7、百分比 10%）不丢。"""
        out = compress("Python 字典自 3.7 起保插入序", "xizi")
        self.assertIn("3.7", out)

    def test_heihua_replaces_jargon(self) -> None:
        """A股黑话档：白话 → 黑话。"""
        out = compress("在股价低位时买入", "heihua")
        self.assertEqual(out, "抄底")

    def test_unknown_level_raises(self) -> None:
        with self.assertRaises(ValueError):
            compress("文本", "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
