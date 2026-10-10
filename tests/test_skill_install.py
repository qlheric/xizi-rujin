"""装进一个干净的 HOME 之后，SKILL.md 写的命令必须能在无关项目里跑。

不 import 仓库里的包：只跑 install.sh，再按装好的 SKILL.md 原文去调入口。
当前 main 只复制 SKILL.md、命令仍是 python -m eval.*，这条测试应当失败。
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# SKILL.md 里必须原样出现的三行。测试按这三行替换占位符再执行。
SCAN_LINE = 'python "$SKILL_DIR/xizi_rujin.py" scan <测试文件或目录>'
MUTATE_LINE = 'python "$SKILL_DIR/xizi_rujin.py" mutate <源文件.py> --cmd "<测试命令>"'
AUDIT_LINE = (
    'python "$SKILL_DIR/xizi_rujin.py" audit --source <源文件.py> '
    '--cmd "<测试命令>" <测试文件或目录>'
)


class SkillInstallE2E(unittest.TestCase):
    def test_fresh_install_runs_documented_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as home_s, tempfile.TemporaryDirectory() as proj_s, tempfile.TemporaryDirectory() as bin_s:
            home = Path(home_s)
            proj = Path(proj_s)
            bindir = Path(bin_s)
            for name in ("claude", "codex", "opencode"):
                stub = bindir / name
                stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env.pop("PYTHONPATH", None)
            env.pop("OPENCODE_CONFIG", None)

            installed = subprocess.run(
                ["bash", str(ROOT / "install.sh")],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                installed.returncode,
                0,
                installed.stdout + installed.stderr,
            )
            with self.subTest("install hint"):
                self.assertNotIn("省 token", installed.stdout)

            claude = home / ".claude" / "skills" / "xizi-rujin"
            codex = home / ".codex" / "skills" / "xizi-rujin"
            opencode = home / ".config" / "opencode" / "skills" / "xizi-rujin"
            skill_text = ""
            for label, skill_dir in (
                ("claude", claude),
                ("codex", codex),
                ("opencode", opencode),
            ):
                with self.subTest("bundle", harness=label):
                    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                    front = skill_text.split("---", 2)[1]
                    self.assertRegex(front, r"(?m)^name:\s*xizi-rujin\s*$")
                    for line in (SCAN_LINE, MUTATE_LINE, AUDIT_LINE):
                        self.assertIn(line, skill_text)
                    self.assertTrue((skill_dir / "xizi_rujin.py").is_file())
                    self.assertTrue((skill_dir / "eval" / "fake_green.py").is_file())
                    self.assertTrue((skill_dir / "eval" / "mutation_test.py").is_file())
                    self.assertNotIn("python -m eval.fake_green", skill_text)
                    self.assertNotIn("python -m eval.mutation_test", skill_text)

            self._write_foreign_project(proj)
            py = sys.executable

            with self.subTest("scan empty"):
                empty = self._run(claude, ["scan", "empty_tests"], proj, env)
                self.assertIn("无法判定", empty.stdout, empty.stderr)
                self.assertEqual(empty.returncode, 2, empty.stdout + empty.stderr)

            with self.subTest("mutate fake"):
                fake = self._run(
                    claude,
                    ["mutate", "demo_math.py", "--cmd", f"{py} test_fake.py"],
                    proj,
                    env,
                )
                self.assertIn("结论：打回", fake.stdout, fake.stderr)
                self.assertNotEqual(fake.returncode, 0)

            with self.subTest("mutate real"):
                real = self._run(
                    codex,
                    ["mutate", "demo_math.py", "--cmd", f"{py} test_real.py"],
                    proj,
                    env,
                )
                self.assertIn("结论：通过", real.stdout, real.stderr)
                self.assertEqual(real.returncode, 0, real.stdout + real.stderr)

            # 静态扫描已经看见 assert True，变异即使全杀也不能单独算通过。
            with self.subTest("audit overrides a green mutation"):
                audit = self._run(
                    claude,
                    [
                        "audit",
                        "--source",
                        "demo_math.py",
                        "--cmd",
                        f"{py} suite/test_real.py",
                        "suite",
                    ],
                    proj,
                    env,
                )
                self.assertIn("结论：通过", audit.stdout, audit.stderr)
                self.assertIn(
                    "结论：打回——静态扫描发现疑似假绿，变异得分不能单独算通过。",
                    audit.stdout,
                    audit.stderr,
                )
                self.assertEqual(audit.returncode, 1, audit.stdout + audit.stderr)

            with self.subTest("audit empty dir stops"):
                stopped = self._run(
                    claude,
                    [
                        "audit",
                        "--source",
                        "demo_math.py",
                        "--cmd",
                        f"{py} test_real.py",
                        "empty_tests",
                    ],
                    proj,
                    env,
                )
                self.assertIn("无法判定", stopped.stdout, stopped.stderr)
                self.assertNotIn("结论：通过", stopped.stdout)
                self.assertNotIn("结论：打回", stopped.stdout)
                self.assertEqual(stopped.returncode, 2, stopped.stdout + stopped.stderr)

            with self.subTest("audit static finding beats a red baseline"):
                beaten = self._run(
                    codex,
                    [
                        "audit",
                        "--source",
                        "demo_math.py",
                        "--cmd",
                        f"{py} definitely_missing.py",
                        "test_fake.py",
                    ],
                    proj,
                    env,
                )
                self.assertIn("结论：打回——静态扫描发现疑似假绿。", beaten.stdout, beaten.stderr)
                self.assertEqual(beaten.returncode, 1, beaten.stdout + beaten.stderr)

            with self.subTest("audit clean"):
                clean = self._run(
                    codex,
                    [
                        "audit",
                        "--source",
                        "demo_math.py",
                        "--cmd",
                        f"{py} test_real.py",
                        "test_real.py",
                    ],
                    proj,
                    env,
                )
                self.assertIn("结论：通过", clean.stdout, clean.stderr)
                self.assertNotIn("结论：打回", clean.stdout)
                self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

            # 三行命令确实写在装好的 SKILL.md 里，而不是测试自己发明的。
            with self.subTest("documented lines"):
                self.assertIn(SCAN_LINE, skill_text)
                self.assertIn(MUTATE_LINE, skill_text)
                self.assertIn(AUDIT_LINE, skill_text)

    def _write_foreign_project(self, proj: Path) -> None:
        (proj / "demo_math.py").write_text(
            textwrap.dedent(
                """\
                def add(a, b):
                    return a + b
                """
            ),
            encoding="utf-8",
        )
        (proj / "test_fake.py").write_text("assert True\n", encoding="utf-8")
        (proj / "test_real.py").write_text(
            "from demo_math import add\nassert add(1, 2) == 3\n",
            encoding="utf-8",
        )
        suite = proj / "suite"
        suite.mkdir()
        # 脚本目录不是项目根，测试自己把项目根加进路径，变异命令才能 import。
        (suite / "test_real.py").write_text(
            textwrap.dedent(
                """\
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
                from demo_math import add
                assert add(1, 2) == 3
                """
            ),
            encoding="utf-8",
        )
        (suite / "test_cheat.py").write_text("assert True\n", encoding="utf-8")
        (proj / "empty_tests").mkdir()

    def _run(self, skill_dir: Path, args: list[str], cwd: Path, env: dict[str, str]):
        # 与 SKILL.md 的写法一致：解释器 + 技能目录里的入口，cwd 是用户项目。
        return subprocess.run(
            [sys.executable, str(skill_dir / "xizi_rujin.py"), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
