"""README 里的命令输出和安装参数必须和仓库里的工具一致。

演示块改了、工具输出没改，或者反过来，这里会失败。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _marked(name: str) -> str:
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    begin = README.index(start) + len(start)
    finish = README.index(end, begin)
    lines = README[begin:finish].strip("\n").splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip("\n") + "\n"


def _run(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class ReadmeMatchesTool(unittest.TestCase):
    def test_demo_blocks_match_a_fresh_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "demo_math.py").write_text(_marked("file:demo_math.py"), encoding="utf-8")
            (repo / "test.py").write_text(_marked("file:test.py"), encoding="utf-8")
            (repo / "test_real.py").write_text(_marked("file:test_real.py"), encoding="utf-8")
            (repo / "empty").mkdir()

            fake = _run(repo, ["-m", "eval.mutation_test", "demo_math.py", "--cmd", f"{sys.executable} test.py"])
            self.assertEqual(fake.returncode, 1, fake.stderr)
            self.assertEqual(fake.stdout.strip(), _marked("demo-fake").strip())

            real = _run(repo, ["-m", "eval.mutation_test", "demo_math.py", "--cmd", f"{sys.executable} test_real.py"])
            self.assertEqual(real.returncode, 0, real.stderr)
            self.assertEqual(real.stdout.strip(), _marked("demo-real").strip())

            scan = _run(repo, ["-m", "eval.fake_green", "test.py"])
            self.assertEqual(scan.returncode, 1, scan.stderr)
            self.assertEqual(scan.stdout.strip(), _marked("demo-scan").strip())

            empty = _run(repo, ["-m", "eval.fake_green", "empty"])
            self.assertEqual(empty.returncode, 2, empty.stderr)
            self.assertEqual(empty.stdout.strip(), _marked("demo-empty").strip())

    def test_documented_flags_exist(self) -> None:
        install_sh = (ROOT / "install.sh").read_text(encoding="utf-8")
        install_ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
        action = (ROOT / ".github" / "actions" / "xizi-audit" / "action.yml").read_text(encoding="utf-8")
        self.assertIn("--hook project", README)
        self.assertIn("--hook user", README)
        self.assertIn('"$HOOK_SCOPE" != "project"', install_sh)
        self.assertIn('"$HOOK_SCOPE" != "user"', install_sh)
        self.assertIn("-Hook project", README)
        self.assertIn("-Hook user", README)
        self.assertIn('ValidateSet("", "project", "user")', install_ps1)
        self.assertIn("audit --changed", README)
        self.assertIn("--base", README)
        self.assertIn("qlheric/xizi-rujin/.github/actions/xizi-audit@main", README)
        self.assertIn("audit --changed", action)
        self.assertNotIn("省 token", README)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONIOENCODING"] = "utf-8"
        help_text = subprocess.run(
            [sys.executable, "-m", "xizi_rujin", "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        self.assertIn("audit --changed", help_text)
        changed = subprocess.run(
            [sys.executable, "-m", "xizi_rujin", "audit", "--changed", "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        self.assertIn("--base", changed)
        self.assertIn("--timeout", changed)

    def test_group4_rates_match_the_readme(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        for args in (["-m", "eval.bench"], ["-m", "eval.bench", "--dir", "eval/traps_v2"]):
            proc = subprocess.run(
                [sys.executable, *args],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("组 4 错误放行率：1/10（10%）", proc.stdout)
        self.assertIn("trap_06_hardcode_wrong", README)
        self.assertIn("v2_07_avg_pos", README)
        self.assertIn("历史记录", README)
        self.assertIn("这次没有重跑", README)


if __name__ == "__main__":
    unittest.main()
