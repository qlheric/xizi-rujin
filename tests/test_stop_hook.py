"""Stop 钩子必须拦住假绿，并在工具自己出错时放行。

这些用例在没有 hook-stop / audit --changed 的 main 上应当失败：
子进程退出码是 2（未知子命令），stdout 里没有 decision。
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def init_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "dev")
    # Windows 上 autocrlf 会把整份文件标成改动，行号过滤就失真。
    _git(repo, "config", "core.autocrlf", "false")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")


def stop_payload(
    repo: Path,
    *,
    session_id: str = "sess-1",
    stop_hook_active: bool = False,
    background_tasks: list | None = None,
) -> dict:
    """形状对齐 Claude Code / Codex 的 Stop 输入。"""
    return {
        "session_id": session_id,
        "transcript_path": str(repo / "transcript.jsonl"),
        "cwd": str(repo),
        "permission_mode": "default",
        "hook_event_name": "Stop",
        "stop_hook_active": stop_hook_active,
        "last_assistant_message": "测试全过了。",
        "background_tasks": [] if background_tasks is None else background_tasks,
    }


def run_hook(repo: Path, payload: dict, *, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("XIZI_STOP_HOOK_CRASH", None)
    if extra_env:
        env.update(extra_env)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "xizi_rujin", "hook-stop"],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=repo,
        env=env,
    )


def _posix(path: Path) -> str:
    """Git Bash 认 /c/Users/...，不认带反斜杠的 Windows 路径。"""
    if os.name != "nt":
        return str(path)
    drive, rest = os.path.splitdrive(str(path.resolve()))
    if not drive:
        return rest.replace("\\", "/")
    return "/" + drive[0].lower() + rest.replace("\\", "/")


def working_bash() -> str:
    """跳过 System32 里那个没装发行版就会失败的 WSL bash.exe。"""
    candidates: list[str] = []
    if os.name == "nt":
        for key in ("ProgramFiles", "ProgramFiles(x86)"):
            root = os.environ.get(key)
            if not root:
                continue
            candidates.append(str(Path(root) / "Git" / "bin" / "bash.exe"))
            candidates.append(str(Path(root) / "Git" / "usr" / "bin" / "bash.exe"))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen or not Path(candidate).is_file():
            continue
        seen.add(candidate)
        probe = subprocess.run(
            [candidate, "-c", "echo ok"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if probe.returncode == 0 and "ok" in (probe.stdout or ""):
            return candidate
    raise AssertionError(
        "找不到能执行脚本的 bash。Windows 上 PATH 里的 bash 经常是没装发行版的 WSL。"
    )


def run_cli(repo: Path, args: list[str], *, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "xizi_rujin", *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=repo,
        env=env,
    )


def write_fake_green(repo: Path) -> None:
    (repo / "demo_math.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (repo / "test_demo.py").write_text("assert True\n", encoding="utf-8")


def write_real_pair(repo: Path) -> None:
    (repo / "demo_math.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (repo / "test_demo.py").write_text(
        "from demo_math import add\nassert add(1, 2) == 3\n",
        encoding="utf-8",
    )


class StopHookE2E(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "proj"
        self.repo.mkdir()
        self.state = Path(self._tmp.name) / "state"
        self.state.mkdir()
        init_repo(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _env(self, **extra: str) -> dict[str, str]:
        base = {"XIZI_STOP_HOOK_STATE_DIR": str(self.state)}
        base.update(extra)
        return base

    def test_fake_green_change_is_blocked_with_reason(self) -> None:
        write_fake_green(self.repo)
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="fake"),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data.get("decision"), "block")
        self.assertIn("打回", data.get("reason", ""))

    def test_real_test_change_is_allowed(self) -> None:
        (self.repo / "demo_math.py").write_text(
            "def add(a, b):\n    return a + b\n",
            encoding="utf-8",
        )
        _git(self.repo, "add", "demo_math.py")
        _git(self.repo, "commit", "-m", "source")
        (self.repo / "test_demo.py").write_text(
            "from demo_math import add\nassert add(1, 2) == 3\n",
            encoding="utf-8",
        )
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="real"),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")
        self.assertNotIn("decision", proc.stdout)

    def test_no_relevant_change_is_allowed_fast(self) -> None:
        readme = self.repo / "README.md"
        readme.write_text("base\nstill docs\n", encoding="utf-8")
        started = time.monotonic()
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="docs"),
            extra_env=self._env(),
        )
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")
        self.assertLess(elapsed, 3.0, f"无改动却花了 {elapsed:.2f}s")

    def test_stop_hook_active_allows_even_if_fake_green(self) -> None:
        write_fake_green(self.repo)
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="loop", stop_hook_active=True),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_retry_cap_allows_to_avoid_a_loop(self) -> None:
        write_fake_green(self.repo)
        env = self._env(XIZI_STOP_HOOK_MAX_BLOCKS="1")
        first = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="cap"),
            extra_env=env,
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(json.loads(first.stdout).get("decision"), "block")
        second = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="cap"),
            extra_env=env,
        )
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(second.stdout.strip(), "")

    def test_tool_crash_fails_open_with_warning(self) -> None:
        write_fake_green(self.repo)
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="crash"),
            extra_env=self._env(XIZI_STOP_HOOK_CRASH="1"),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertNotEqual(data.get("decision"), "block")
        message = data.get("systemMessage", "")
        self.assertIn("放行", message)
        self.assertTrue("出错" in message or "崩溃" in message)

    def test_source_without_test_is_blocked_as_undecided(self) -> None:
        (self.repo / "demo_math.py").write_text(
            "def add(a, b):\n    return a + b\n",
            encoding="utf-8",
        )
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="notest"),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data.get("decision"), "block")
        self.assertIn("无法判定", data.get("reason", ""))

    def test_background_tasks_allow_without_auditing(self) -> None:
        write_fake_green(self.repo)
        proc = run_hook(
            self.repo,
            stop_payload(
                self.repo,
                session_id="bg",
                background_tasks=[{"id": "shell-1", "status": "running"}],
            ),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_only_changed_function_is_mutated(self) -> None:
        """没改到的函数如果也被变异，窄测试会被打成假绿。"""
        (self.repo / "demo_math.py").write_text(
            textwrap.dedent(
                """\
                def unused(x):
                    return x + 10

                def add(a, b):
                    return a + b
                """
            ),
            encoding="utf-8",
        )
        (self.repo / "test_demo.py").write_text(
            "from demo_math import add\nassert add(1, 2) == 3\n",
            encoding="utf-8",
        )
        _git(self.repo, "add", "demo_math.py", "test_demo.py")
        _git(self.repo, "commit", "-m", "both")
        source = (self.repo / "demo_math.py").read_text(encoding="utf-8")
        source = source.replace("return a + b", "return a + b  # touched")
        (self.repo / "demo_math.py").write_text(source, encoding="utf-8")
        proc = run_hook(
            self.repo,
            stop_payload(self.repo, session_id="scoped"),
            extra_env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip(), "", proc.stdout + proc.stderr)


class ChangedAuditCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "proj"
        self.repo.mkdir()
        init_repo(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_changed_fake_green_exits_1(self) -> None:
        write_fake_green(self.repo)
        proc = run_cli(self.repo, ["audit", "--changed"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("打回", proc.stdout)

    def test_changed_real_test_exits_0(self) -> None:
        (self.repo / "demo_math.py").write_text(
            "def add(a, b):\n    return a + b\n",
            encoding="utf-8",
        )
        _git(self.repo, "add", "demo_math.py")
        _git(self.repo, "commit", "-m", "source")
        (self.repo / "test_demo.py").write_text(
            "from demo_math import add\nassert add(1, 2) == 3\n",
            encoding="utf-8",
        )
        proc = run_cli(self.repo, ["audit", "--changed"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("通过", proc.stdout)
        self.assertNotIn("打回", proc.stdout)

    def test_changed_nothing_relevant_exits_0(self) -> None:
        (self.repo / "README.md").write_text("docs only\n", encoding="utf-8")
        proc = run_cli(self.repo, ["audit", "--changed"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("通过", proc.stdout)

    def test_changed_without_test_exits_2(self) -> None:
        (self.repo / "demo_math.py").write_text(
            "def add(a, b):\n    return a + b\n",
            encoding="utf-8",
        )
        proc = run_cli(self.repo, ["audit", "--changed"])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("无法判定", proc.stdout)

    def test_base_ref_audits_the_committed_diff(self) -> None:
        write_real_pair(self.repo)
        _git(self.repo, "add", "demo_math.py", "test_demo.py")
        _git(self.repo, "commit", "-m", "real")
        _git(self.repo, "branch", "base")
        (self.repo / "test_demo.py").write_text("assert True\n", encoding="utf-8")
        _git(self.repo, "add", "test_demo.py")
        _git(self.repo, "commit", "-m", "fake")
        proc = run_cli(self.repo, ["audit", "--changed", "--base", "base"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("打回", proc.stdout)

    def test_job_summary_records_the_verdict(self) -> None:
        write_fake_green(self.repo)
        summary = Path(self._tmp.name) / "summary.md"
        proc = run_cli(
            self.repo,
            ["audit", "--changed"],
            extra_env={"GITHUB_STEP_SUMMARY": str(summary)},
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        text = summary.read_text(encoding="utf-8")
        self.assertIn("打回", text)


class LineScopedMutants(unittest.TestCase):
    def test_only_lines_skips_untouched_functions(self) -> None:
        from eval.mutation_test import generate_mutants

        source = "def keep(x):\n    return x + 1\n\ndef touch(x):\n    return x + 2\n"
        limited = generate_mutants(source, only_lines={5})
        self.assertTrue(limited)
        for text, _desc in limited:
            self.assertIn("return x + 1", text)
            self.assertNotIn("return x - 1", text)


class HookInstall(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "home"
        self.proj = Path(self._tmp.name) / "proj"
        self.home.mkdir()
        self.proj.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _install(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["HOME"] = str(self.home)
        env["USERPROFILE"] = str(self.home)
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, "-m", "xizi_rujin", "install-hook", *args],
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=self.proj,
            env=env,
        )

    def _uninstall(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["HOME"] = str(self.home)
        env["USERPROFILE"] = str(self.home)
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, "-m", "xizi_rujin", "uninstall-hook", *args],
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=self.proj,
            env=env,
        )

    def test_project_claude_merges_without_clobber(self) -> None:
        settings = self.proj / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(
            json.dumps(
                {
                    "permissions": {"allow": ["Bash"]},
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [{"type": "command", "command": "echo", "args": ["hi"]}],
                            }
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        proc = self._install("--scope", "project", "--harness", "claude")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(data["permissions"]["allow"], ["Bash"])
        self.assertEqual(data["hooks"]["PreToolUse"][0]["hooks"][0]["command"], "echo")
        stop_hooks = data["hooks"]["Stop"]
        commands = [h for group in stop_hooks for h in group.get("hooks", [])]
        self.assertEqual(len(commands), 1)
        self.assertIn("hook-stop", commands[0].get("args", []) + [commands[0].get("command", "")])
        again = self._install("--scope", "project", "--harness", "claude")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        data2 = json.loads(settings.read_text(encoding="utf-8"))
        commands2 = [h for group in data2["hooks"]["Stop"] for h in group.get("hooks", [])]
        self.assertEqual(len(commands2), 1)

    def test_invalid_json_is_not_overwritten(self) -> None:
        settings = self.proj / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{ not json", encoding="utf-8")
        proc = self._install("--scope", "project", "--harness", "claude")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("JSON", proc.stderr + proc.stdout)
        self.assertEqual(settings.read_text(encoding="utf-8"), "{ not json")

    def test_uninstall_removes_only_our_hook(self) -> None:
        proc = self._install("--scope", "project", "--harness", "claude")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        settings = self.proj / ".claude" / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["hooks"]["Stop"].append(
            {"hooks": [{"type": "command", "command": "echo", "args": ["keep"]}]}
        )
        settings.write_text(json.dumps(data), encoding="utf-8")
        removed = self._uninstall("--scope", "project", "--harness", "claude")
        self.assertEqual(removed.returncode, 0, removed.stdout + removed.stderr)
        left = json.loads(settings.read_text(encoding="utf-8"))
        commands = [h for group in left["hooks"].get("Stop", []) for h in group.get("hooks", [])]
        self.assertEqual([h["command"] for h in commands], ["echo"])

    def test_user_codex_hooks_json(self) -> None:
        proc = self._install("--scope", "user", "--harness", "codex")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        path = self.home / ".codex" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        commands = [h for group in data["hooks"]["Stop"] for h in group.get("hooks", [])]
        self.assertEqual(len(commands), 1)
        self.assertTrue(commands[0].get("args"))
        self.assertNotIn("continue", json.dumps(data))

    def _run_install_sh(self, bash: str, bindir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["USERPROFILE"] = str(self.home)
        env["PYTHONIOENCODING"] = "utf-8"
        # $0 占位，后面两个参数在 bash 里改成 POSIX 的 HOME 和 PATH，再 exec 脚本。
        # $BASH 是当前这个能跑的解释器。不要再去 PATH 里找 bash，Windows 上那是 WSL。
        command = 'export HOME="$1"; shift; export PATH="$1:$PATH"; shift; script="$1"; shift; exec "$BASH" "$script" "$@"'
        return subprocess.run(
            [
                bash,
                "-c",
                command,
                "bash",
                _posix(self.home),
                _posix(bindir),
                str(ROOT / "install.sh"),
                *args,
            ],
            cwd=self.proj,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_install_sh_hook_flag_is_opt_in(self) -> None:
        bash = working_bash()
        bindir = Path(self._tmp.name) / "bin"
        bindir.mkdir()
        for name in ("claude", "codex", "opencode"):
            stub = bindir / name
            stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            # Git Bash 的 command -v 按 PATHEXT 找 .cmd，认不出没后缀的脚本。
            if os.name == "nt":
                cmd = bindir / f"{name}.cmd"
                cmd.write_text("@exit /b 0\r\n", encoding="ascii")
        plain = self._run_install_sh(bash, bindir, [])
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        self.assertFalse((self.proj / ".claude" / "settings.json").exists())
        hooked = self._run_install_sh(bash, bindir, ["--hook", "project"])
        self.assertEqual(hooked.returncode, 0, hooked.stdout + hooked.stderr)
        settings = json.loads((self.proj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Stop", settings["hooks"])
        codex = json.loads((self.proj / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("Stop", codex["hooks"])


class ActionExample(unittest.TestCase):
    def test_example_workflow_invokes_changed_audit(self) -> None:
        action = (ROOT / ".github" / "actions" / "xizi-audit" / "action.yml").read_text(encoding="utf-8")
        example = (ROOT / ".github" / "workflows" / "xizi-audit.example.yml").read_text(encoding="utf-8")
        self.assertIn("audit", action)
        self.assertIn("--changed", action)
        self.assertIn("xizi-audit", example)
        self.assertNotIn("on:\n  pull_request", example)


if __name__ == "__main__":
    unittest.main()
