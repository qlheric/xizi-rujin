"""audit_changed.test_command：unittest 假绿回归。

无 unittest.main 时直接 python 文件会 0 测试却 exit 0；
含 TestCase 时必须走 discover，失败/零测试非 0，通过为 0。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xizi_rujin.audit_changed import test_command


def _run(cmd: str, cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class TestCommandUnittest(unittest.TestCase):
    def test_failing_unittest_without_main_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test_fail_no_main.py"
            path.write_text(
                "import unittest\n"
                "\n"
                "class T(unittest.TestCase):\n"
                "    def test_boom(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            proc = _run(test_command([path]), tmp)
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_passing_unittest_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test_pass.py"
            path.write_text(
                "import unittest\n"
                "\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertEqual(1, 1)\n",
                encoding="utf-8",
            )
            proc = _run(test_command([path]), tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_plain_assert_script_unchanged(self) -> None:
        """非 unittest 仍直接执行文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test_plain.py"
            path.write_text("assert 1 + 1 == 2\n", encoding="utf-8")
            cmd = test_command([path])
            self.assertNotIn("-m unittest", cmd)
            proc = _run(cmd, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
