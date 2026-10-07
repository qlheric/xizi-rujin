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

    def test_astock_expanded(self) -> None:
        """A股估值缩写：市盈率 → PE。"""
        self.assertEqual(compress("市盈率", "astock"), "PE")

    def test_internet_abbr(self) -> None:
        """互联网缩写：关键绩效指标 → KPI。"""
        self.assertEqual(compress("关键绩效指标", "internet"), "KPI")

    def test_gongwen_compression(self) -> None:
        """公文套话压缩：深入贯彻落实 → 落实。"""
        self.assertEqual(compress("深入贯彻落实", "gongwen"), "落实")

    def test_cyber_slang(self) -> None:
        """网络梗：永远的神 → yyds。"""
        self.assertEqual(compress("永远的神", "cyber"), "yyds")

    def test_gaming_terms(self) -> None:
        """电竞术语：远程物理输出核心 → ADC。"""
        self.assertEqual(compress("远程物理输出核心", "gaming"), "ADC")

    def test_medical_abbr(self) -> None:
        """医疗缩写：急性心肌梗死 → 心梗。"""
        self.assertEqual(compress("急性心肌梗死", "medical"), "心梗")

    def test_acg_terms(self) -> None:
        """二次元术语：动画剧集 → 番。"""
        self.assertEqual(compress("动画剧集", "acg"), "番")

    def test_romance_terms(self) -> None:
        """恋爱术语：心动对象 → crush。"""
        self.assertEqual(compress("心动对象", "romance"), "crush")

    def test_workplace_terms(self) -> None:
        """职场黑话：被公司辞退 → 毕业。"""
        self.assertEqual(compress("被公司辞退", "workplace"), "毕业")

    def test_fandom_terms(self) -> None:
        """饭圈黑话：偶像塌房 → 塌房。"""
        self.assertEqual(compress("偶像塌房", "fandom"), "塌房")

    def test_academic_terms(self) -> None:
        """学术黑话：考研成功上岸 → 上岸。"""
        self.assertEqual(compress("考研成功上岸", "academic"), "上岸")

    def test_cantonese_terms(self) -> None:
        """粤语：没有 → 冇。"""
        self.assertEqual(compress("没有", "cantonese"), "冇")

    def test_food_terms(self) -> None:
        """美食黑话：吃饭 → 干饭。"""
        self.assertEqual(compress("吃饭", "food"), "干饭")

    def test_all_domains_registered(self) -> None:
        """所有领域档位都能被识别，且每个档位都有规则、输出为字符串。"""
        from xizi.compressor import RULES_BY_LEVEL

        self.assertTrue(len(RULES_BY_LEVEL) >= 23)
        for level in RULES_BY_LEVEL:
            self.assertIsInstance(compress("测试", level), str)

    def test_legal_terms(self) -> None:
        self.assertEqual(compress("依法追究刑事责任", "legal"), "追刑责")

    def test_fitness_terms(self) -> None:
        self.assertEqual(compress("力量训练", "fitness"), "撸铁")

    def test_pet_terms(self) -> None:
        self.assertEqual(compress("养猫的铲屎官", "pet"), "铲屎官")

    def test_auto_terms(self) -> None:
        self.assertEqual(compress("涡轮增压发动机", "auto"), "涡轮")

    def test_beauty_terms(self) -> None:
        self.assertEqual(compress("敏感性皮肤", "beauty"), "敏感肌")

    def test_unknown_level_raises(self) -> None:
        with self.assertRaises(ValueError):
            compress("文本", "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
