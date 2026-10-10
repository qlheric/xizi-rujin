"""变异测试器不得自己制造假绿。

每条都对应一个曾经能把「没测」说成「通过」的入口：基线不绿、字节码缓存、
阈值各写各的、超时把整个进程打崩、结论行只写在文档里。
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.bench import group4_tool
from eval.mutation_test import main, run_mutation


def _run_main(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


class MutationReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self) -> None:
        os.chdir(self._old)
        self._tmp.cleanup()

    def _write(self, name: str, text: str) -> str:
        path = os.path.join(self._tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_baseline_failure_is_inconclusive(self) -> None:
        """原始测试本来就是红的，不许报 100% 通过。"""
        src = self._write("demo_math.py", "def add(a, b):\n    return a + b\n")
        self._write("test_fail.py", "import sys\nraise SystemExit(1)\n")
        cmd = f'"{sys.executable}" test_fail.py'
        rc, out = _run_main([src, "--cmd", cmd])
        self.assertNotEqual(rc, 0)
        self.assertIn("无法判定", out)
        self.assertNotIn("结论：通过", out)
        self.assertNotIn("100%", out)
        with open(src, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "def add(a, b):\n    return a + b\n")

    def test_wrong_command_is_inconclusive(self) -> None:
        """测试命令写错（pytset nope）也是基线不绿，不是满分。"""
        src = self._write("demo_math.py", "def add(a, b):\n    return a + b\n")
        rc, out = _run_main([src, "--cmd", "pytset nope"])
        self.assertNotEqual(rc, 0)
        self.assertIn("无法判定", out)
        self.assertNotIn("结论：通过", out)
        self.assertNotIn("100%", out)

    def test_zero_score_prints_readme_rejection(self) -> None:
        """README 演示里的「结论：打回」必须是工具自己打出来的。"""
        src = self._write("demo_math.py", "def add(a, b):\n    return a + b\n")
        self._write("test_true.py", "assert True\n")
        cmd = f'"{sys.executable}" test_true.py'
        rc, out = _run_main([src, "--cmd", cmd])
        self.assertNotEqual(rc, 0)
        self.assertIn("结论：打回——测试抓不住任何 bug，这个「通过」不算数。", out)

    def test_real_assert_can_pass(self) -> None:
        src = self._write("demo_math.py", "def add(a, b):\n    return a + b\n")
        self._write(
            "test_add.py",
            "from demo_math import add\nassert add(1, 2) == 3\n",
        )
        cmd = f'"{sys.executable}" test_add.py'
        rc, out = _run_main([src, "--cmd", cmd])
        self.assertEqual(rc, 0, out)
        self.assertIn("结论：通过", out)
        self.assertIn("100%", out)

    def test_half_score_is_rejected_at_shared_threshold(self) -> None:
        """50% 旧退出码当通过；统一阈值 80% 之后必须打回。"""
        src = self._write("sut.py", "def f(x):\n    return x + 0\n")
        self._write("test_f.py", "from sut import f\nassert f(3) == 3\n")
        cmd = f'"{sys.executable}" test_f.py'
        rc, out = _run_main([src, "--cmd", cmd])
        self.assertNotEqual(rc, 0, out)
        self.assertIn("结论：打回", out)
        self.assertIn("50%", out)
        from eval.mutation_test import PASS_THRESHOLD

        self.assertEqual(PASS_THRESHOLD, 0.8)

    def test_threshold_boundaries(self) -> None:
        from eval.mutation_test import PASS_THRESHOLD, verdict_from_score

        self.assertEqual(PASS_THRESHOLD, 0.8)
        self.assertEqual(verdict_from_score(0.8), "通过")
        self.assertEqual(verdict_from_score(1.0), "通过")
        self.assertEqual(verdict_from_score(0.799), "打回")
        self.assertEqual(verdict_from_score(0.5), "打回")

    def test_timeout_counts_as_killed(self) -> None:
        """死循环变异体算被杀（超时），不能把整个工具打崩。"""
        src = self._write(
            "sut.py",
            "def f(n):\n    while n > 0:\n        n = n + 0\n    return 1\n",
        )
        with open(src, encoding="utf-8") as fh:
            original = fh.read()
        self._write("test_f.py", "from sut import f\nassert f(0) == 1\n")
        cmd = f'"{sys.executable}" test_f.py'
        buf = io.StringIO()
        with redirect_stdout(buf):
            report = run_mutation(src, cmd, timeout=1)
        out = buf.getvalue()
        self.assertIn("超时", out)
        self.assertEqual(report.verdict, "打回")
        self.assertGreaterEqual(report.killed, 1)
        with open(src, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)

    def test_same_length_mutants_ignore_stale_pyc(self) -> None:
        """同长度、同一秒写入时，旧 .pyc 不得把该被杀的变异体判成存活。

        把每次写盘的 mtime 钉死，这样失败不依赖「刚好跨秒」这种运气。
        """
        src = self._write(
            "mod.py",
            "def f(x):\n    return True if x else True\n",
        )
        with open(src, encoding="utf-8") as fh:
            original = fh.read()
        self._write("test_mod.py", "from mod import f\nassert f(False) is True\n")
        cmd = f'"{sys.executable}" test_mod.py'
        fixed = 1_700_000_000
        real_open = open

        def wrapped(file, mode="r", *args, **kwargs):
            fh = real_open(file, mode, *args, **kwargs)
            path = file if isinstance(file, str) else None
            if path and os.path.basename(path) == "mod.py" and "w" in str(mode):
                orig_close = fh.close

                def close():
                    orig_close()
                    os.utime(path, (fixed, fixed))

                fh.close = close
            return fh

        buf = io.StringIO()
        with mock.patch("builtins.open", wrapped):
            with redirect_stdout(buf):
                run_mutation(src, cmd)
        out = buf.getvalue()
        killed = [line for line in out.splitlines() if line.strip().startswith("变异体") and "被杀" in line]
        survived = [line for line in out.splitlines() if line.strip().startswith("变异体") and "存活" in line]
        # return None 被杀；else 分支 True→False 必须被杀；then 分支存活。
        self.assertEqual(len(killed), 2, out)
        self.assertEqual(len(survived), 1, out)
        with open(src, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)

    def test_no_mutants_is_inconclusive(self) -> None:
        src = self._write("sut.py", "def f():\n    pass\n")
        self._write("test_f.py", "from sut import f\nf()\n")
        cmd = f'"{sys.executable}" test_f.py'
        rc, out = _run_main([src, "--cmd", cmd])
        self.assertNotEqual(rc, 0, out)
        self.assertIn("无法判定", out)
        self.assertNotIn("100%", out)


class BenchThresholdTests(unittest.TestCase):
    def test_group4_release_rates(self) -> None:
        """组 4 放行率锁：v1 2/10，v2 4/10。字节码修正改过个别得分，但没跨过 80% 线。"""
        from eval.bench import group4_tool, load_traps

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for dirname, expected in (("traps", 2), ("traps_v2", 4)):
            traps = load_traps(os.path.join(root, "eval", dirname))
            released = []
            for base, src, test in traps:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ok, _reason = group4_tool(base, src, test)
                if ok:
                    released.append(base)
            self.assertEqual(len(traps), 10, dirname)
            self.assertEqual(len(released), expected, f"{dirname}: {released}")
    def test_bench_uses_shared_threshold_not_perfect_score(self) -> None:
        """真实得分 92%（死分支上的 7→8 存活）。旧 bench 非 100% 即打回；80% 阈值应放行。

        父进程关掉字节码，避免旧实现把这个存活变异体误判成被杀、得分虚高到 100%。
        """
        old_cwd = os.getcwd()
        old_env = os.environ.get("PYTHONDONTWRITEBYTECODE")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.chdir(tmp)
                with open("sut.py", "w", encoding="utf-8") as fh:
                    fh.write("def f(x):\n    return x + 1 + 2 + 3 + 4 if x == 1 else 7\n")
                with open("test_sut.py", "w", encoding="utf-8") as fh:
                    fh.write("from sut import f\nassert f(1) == 11\n")
                released, reason = group4_tool("sut", os.path.join(tmp, "sut.py"), os.path.join(tmp, "test_sut.py"))
        finally:
            os.chdir(old_cwd)
            if old_env is None:
                os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            else:
                os.environ["PYTHONDONTWRITEBYTECODE"] = old_env
        self.assertTrue(released, reason)

    def test_bench_still_rejects_below_threshold(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src = os.path.join(root, "eval", "traps_v2", "v2_01_age_boundary.py")
        test = os.path.join(root, "eval", "traps_v2", "v2_01_age_boundary_test.py")
        released, reason = group4_tool("v2_01_age_boundary", src, test)
        self.assertFalse(released, reason)


if __name__ == "__main__":
    unittest.main()
