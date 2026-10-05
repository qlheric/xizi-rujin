"""命令行入口（确定性压缩器）。

用法：
    python -m xizi.cli [wenyan|xizi|heihua] "要压缩的中文文本"
    或 echo "文本" | python -m xizi.cli [档位]
"""

from __future__ import annotations

import sys

from .compressor import compress

_LEVELS = {"wenyan", "xizi", "heihua"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    level = "xizi"
    text = ""
    if args and args[0] in _LEVELS:
        level = args[0]
        args = args[1:]
    if args:
        text = " ".join(args)
    else:
        text = sys.stdin.read().strip()
    if not text:
        print("用法：python -m xizi.cli [wenyan|xizi|heihua] \"文本\"", file=sys.stderr)
        return 1
    print(compress(text, level))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
