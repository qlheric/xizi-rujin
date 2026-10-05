"""词典注册（可插拔）。

每个领域词典是一个模块，暴露若干「短语 → 压缩」映射 dict。
新增领域 = 新增一个文件 + 在 compressor 的 RULES_BY_LEVEL 里挂上，不改核心逻辑。
"""

from . import astock, wenyan

__all__ = ["wenyan", "astock"]
