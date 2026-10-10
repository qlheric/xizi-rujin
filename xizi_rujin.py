#!/usr/bin/env python3
"""技能目录里的离线入口。

本文件和 eval/、xizi_rujin/ 放在同一层。用户项目里没有这些包也能跑。
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from xizi_rujin.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
