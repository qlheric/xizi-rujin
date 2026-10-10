"""xizi-rujin scan | mutate | audit。

零第三方依赖。技能目录里的 xizi_rujin.py 和 pip/uv 安装的控制台入口都进这里。
"""

from __future__ import annotations

import argparse
import sys

USAGE = """\
用法：
  xizi-rujin scan <测试文件或目录>
  xizi-rujin mutate <源文件.py> --cmd "<测试命令>"
  xizi-rujin audit --source <源文件.py> --cmd "<测试命令>" <测试文件或目录>
  xizi-rujin audit --changed [--base <ref>]
  xizi-rujin hook-stop
  xizi-rujin install-hook --scope project|user [--harness claude|codex|both]
  xizi-rujin uninstall-hook --scope project|user [--harness claude|codex|both]

scan    静态扫疑似假绿。没有扫到测试文件时输出「无法判定」，退出码 2。
mutate  变异测试。通过 / 打回 / 无法判定，退出码 0 / 1 / 2。
audit   先 scan 再 mutate。扫到疑似假绿时，变异得分过线也不能单独算通过。
        --changed 只看这次的 Python 改动（工作区，或 --base 的三点 diff）。
hook-stop  读 Stop 钩子的 JSON。打回和无法判定都拦住；通过和无改动不输出。
"""

_STATIC_OVERRIDES_PASS = "结论：打回——静态扫描发现疑似假绿，变异得分不能单独算通过。"
_STATIC_IS_ENOUGH = "结论：打回——静态扫描发现疑似假绿。"


def _utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def cmd_audit(argv: list[str]) -> int:
    """先静态扫，再变异。扫不到测试文件就停；扫到假绿就盖过「通过」。"""
    ap = argparse.ArgumentParser(prog="xizi-rujin audit")
    ap.add_argument("target", help="测试文件或目录")
    ap.add_argument("--source", required=True, help="被测源文件")
    ap.add_argument("--cmd", required=True, help="测试命令")
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--timeout", type=float, default=None)
    args = ap.parse_args(argv)

    from eval.fake_green import main as scan_main

    scan_rc = scan_main([args.target])
    # 没有测试文件：假绿工具已经打印「无法判定」。再跑变异会把「没东西可扫」说成通过。
    if scan_rc == 2:
        return 2

    from eval.mutation_test import main as mutate_main

    mut_argv = [args.source, "--cmd", args.cmd]
    if args.threshold is not None:
        mut_argv.extend(["--threshold", str(args.threshold)])
    if args.timeout is not None:
        mut_argv.extend(["--timeout", str(args.timeout)])
    mut_rc = mutate_main(mut_argv)
    if scan_rc == 1 and mut_rc == 0:
        print(_STATIC_OVERRIDES_PASS)
        return 1
    if scan_rc == 1 and mut_rc != 1:
        print(_STATIC_IS_ENOUGH)
        return 1
    return mut_rc


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print(USAGE, end="")
        return 2
    if argv[0] in {"-h", "--help"}:
        print(USAGE, end="")
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "scan":
        from eval.fake_green import main as scan_main

        return scan_main(rest)
    if cmd == "mutate":
        from eval.mutation_test import main as mutate_main

        return mutate_main(rest)
    if cmd == "audit":
        if "--changed" in rest:
            from xizi_rujin.audit_changed import main as changed_main

            return changed_main(rest)
        return cmd_audit(rest)
    if cmd == "hook-stop":
        from xizi_rujin.stop_hook import main as hook_main

        return hook_main(rest)
    if cmd == "install-hook":
        from xizi_rujin.install_hook import main as install_main

        return install_main(rest)
    if cmd == "uninstall-hook":
        from xizi_rujin.install_hook import main as install_main

        return install_main(rest, remove=True)
    print(f"未知子命令：{cmd}\n{USAGE}", end="")
    return 2
