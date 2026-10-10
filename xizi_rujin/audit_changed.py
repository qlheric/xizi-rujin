"""只审计这次改过的 Python 文件。

Stop 钩子、`xizi-rujin audit --changed` 和 GitHub Action 共用这里。
git 调用失败是工具故障，抛 ToolFailure，不要当成「通过」。
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.M)
_RANK = {"通过": 0, "无法判定": 1, "打回": 2}


class ToolFailure(RuntimeError):
    """git 不在、不是仓库、或 diff 本身失败。这是工具坏了，不是代码的结论。"""


@dataclass
class AuditOutcome:
    verdict: str
    conclusion: str
    log: str = ""


def quote(text: str) -> str:
    """给 shell=True 的测试命令加引号。路径里的空格在 Windows cmd 和 sh 上都能过。"""
    return '"' + text.replace('"', '\\"') + '"'


def test_command(tests: list[Path]) -> str:
    py = quote(sys.executable)
    if len(tests) == 1:
        return f"{py} {quote(str(tests[0]))}"
    script = "import runpy,sys; [runpy.run_path(p, run_name='__main__') for p in sys.argv[1:]]"
    args = " ".join(quote(str(path)) for path in tests)
    return f"{py} -c {quote(script)} {args}"


def parse_changed_lines(patch: str) -> set[int]:
    """从 -U0 的 diff 里取出新文件一侧的行号。纯删除记到删除点旁边的那一行。"""
    lines: set[int] = set()
    for match in _HUNK.finditer(patch):
        start = int(match.group(1))
        count_text = match.group(2)
        count = int(count_text) if count_text is not None else 1
        if count <= 0:
            if start > 0:
                lines.add(start)
            continue
        lines.update(range(start, start + count))
    return lines


def _git(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise ToolFailure("找不到 git，无法判断这次改了什么。") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ToolFailure(detail or f"git {' '.join(args)} 失败")
    return result.stdout


def _inside_work_tree(repo: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise ToolFailure("找不到 git，无法判断这次改了什么。") from exc
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise ToolFailure(f"不是 git 仓库：{repo}")


def _status_path(line: str) -> str:
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1]
    return path


def collect_changes(repo: Path, base: str | None = None) -> list[tuple[Path, set[int] | None]]:
    """返回 [(绝对路径, 改动行)]。行号为 None 表示整份文件（未跟踪，或 diff 给不出行）。"""
    repo = repo.resolve()
    _inside_work_tree(repo)
    found: list[tuple[Path, set[int] | None]] = []
    if base:
        names = _git(repo, ["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"])
        for rel in names.splitlines():
            if not rel.endswith(".py"):
                continue
            path = repo / rel
            if not path.is_file():
                continue
            patch = _git(repo, ["diff", "-U0", f"{base}...HEAD", "--", rel])
            lines = parse_changed_lines(patch)
            found.append((path, lines or None))
        return found

    status = _git(repo, ["status", "--porcelain=v1", "-uall"])
    for line in status.splitlines():
        if len(line) < 4:
            continue
        rel = _status_path(line)
        if not rel.endswith(".py"):
            continue
        path = repo / rel
        if not path.is_file():
            continue
        if line.startswith("??"):
            found.append((path, None))
            continue
        patch = _git(repo, ["diff", "-U0", "HEAD", "--", rel])
        lines = parse_changed_lines(patch)
        found.append((path, lines or None))
    return found


def _is_test(path: Path) -> bool:
    from eval.fake_green import _is_test_filename

    return _is_test_filename(path.name)


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return out


def tests_for_source(repo: Path, source: Path, changed_tests: list[Path]) -> list[Path]:
    """同目录下的测试都算配套。tests/ 里只按文件名配对，避免一把跑完整套。"""
    found: list[Path] = []
    if source.parent.is_dir():
        for child in sorted(source.parent.glob("*.py")):
            if _is_test(child):
                found.append(child)
    names = {f"test_{source.stem}.py", f"{source.stem}_test.py"}
    for directory in (repo / "tests", source.parent / "tests"):
        if not directory.is_dir() or directory.resolve() == source.parent.resolve():
            continue
        for name in sorted(names):
            candidate = directory / name
            if candidate.is_file():
                found.append(candidate)
    for test in changed_tests:
        if source.stem in test.stem or test.parent.resolve() == source.parent.resolve():
            found.append(test)
    return _dedupe(found)


def sources_for_test(repo: Path, test: Path) -> list[Path]:
    stem = test.stem
    if stem.startswith("test_"):
        stem = stem[len("test_") :]
    elif stem.endswith("_test"):
        stem = stem[: -len("_test")]
    found: list[Path] = []
    for directory in (test.parent, repo):
        candidate = directory / f"{stem}.py"
        if candidate.is_file() and not _is_test(candidate):
            found.append(candidate)
    if found:
        return _dedupe(found)
    for child in sorted(test.parent.glob("*.py")):
        if not _is_test(child):
            found.append(child)
    return _dedupe(found)


def _scan_tests(tests: list[Path]) -> AuditOutcome | None:
    from eval.fake_green import scan_source

    for test in tests:
        try:
            source = test.read_text(encoding="utf-8")
        except OSError as exc:
            raise ToolFailure(f"读不到测试文件 {test.name}：{exc}") from exc
        findings = scan_source(source, str(test))
        if not findings:
            continue
        first = findings[0]
        detail = first.get("detail") or first.get("kind")
        return AuditOutcome(
            "打回",
            f"结论：打回——静态扫描发现疑似假绿（{test.name}：{detail}）。",
        )
    return None


def _audit_pair(
    source: Path | None,
    tests: list[Path],
    only_lines: set[int] | None,
    timeout: float,
) -> AuditOutcome:
    if source is None and not tests:
        return AuditOutcome("通过", "结论：通过——没有需要审计的 Python 改动。")
    if source is not None and not tests:
        return AuditOutcome(
            "无法判定",
            "结论：无法判定——改了 "
            f"{source.name}，但没有找到配套测试（同目录或 tests/ 下的 test*.py、*_test.py）。",
        )
    scanned = _scan_tests(tests)
    if scanned is not None:
        return scanned
    if source is None:
        return AuditOutcome(
            "无法判定",
            "结论：无法判定——改了测试，但没有找到对应的源文件，没法做变异。",
        )
    from eval.mutation_test import PASS_THRESHOLD, _conclusion, run_mutation

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        report = run_mutation(
            str(source),
            test_command(tests),
            timeout=timeout,
            only_lines=only_lines,
        )
    conclusion = _conclusion(report, PASS_THRESHOLD)
    return AuditOutcome(report.verdict, conclusion, buffer.getvalue())


def audit_changed(
    repo: Path | None = None,
    *,
    base: str | None = None,
    timeout: float = 60,
) -> AuditOutcome:
    """审计 repo 里这次的 Python 改动。无相关改动也返回「通过」，由调用方决定要不要出声。"""
    if os.environ.get("XIZI_STOP_HOOK_CRASH") == "1":
        raise RuntimeError("XIZI_STOP_HOOK_CRASH")
    repo = (repo or Path.cwd()).resolve()
    previous = Path.cwd()
    os.chdir(repo)
    try:
        changes = collect_changes(repo, base)
        if not changes:
            return AuditOutcome("通过", "结论：通过——没有需要审计的 Python 改动。")
        sources = [(path, lines) for path, lines in changes if not _is_test(path)]
        tests = [path for path, _lines in changes if _is_test(path)]
        outcomes: list[AuditOutcome] = []
        seen: set[Path] = set()
        for path, lines in sources:
            paired = tests_for_source(repo, path, tests)
            outcomes.append(_audit_pair(path, paired, lines, timeout))
            seen.add(path.resolve())
        for test in tests:
            for source in sources_for_test(repo, test):
                if source.resolve() in seen:
                    continue
                paired = tests_for_source(repo, source, tests)
                outcomes.append(_audit_pair(source, paired or [test], None, timeout))
                seen.add(source.resolve())
            if not sources_for_test(repo, test):
                outcomes.append(_audit_pair(None, [test], None, timeout))
        if not outcomes:
            return AuditOutcome("通过", "结论：通过——没有需要审计的 Python 改动。")
        worst = max(_RANK[item.verdict] for item in outcomes)
        chosen = [item for item in outcomes if _RANK[item.verdict] == worst]
        verdict = chosen[0].verdict
        conclusion = " ".join(item.conclusion for item in chosen)
        log = "".join(item.log for item in outcomes if item.log)
        return AuditOutcome(verdict, conclusion, log)
    finally:
        os.chdir(previous)


def exit_code(verdict: str) -> int:
    if verdict == "通过":
        return 0
    if verdict == "无法判定":
        return 2
    return 1


def append_job_summary(conclusion: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("## 惜字如金\n\n")
        handle.write(conclusion.rstrip() + "\n")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="xizi-rujin audit --changed")
    parser.add_argument("--changed", action="store_true")
    parser.add_argument("--base", default=None, help="与该 ref 做三点 diff，例如 origin/main")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)
    try:
        outcome = audit_changed(
            Path(args.repo) if args.repo else Path.cwd(),
            base=args.base,
            timeout=args.timeout,
        )
    except ToolFailure as exc:
        conclusion = f"结论：无法判定——{exc}"
        print(conclusion)
        append_job_summary(conclusion)
        return 2
    if outcome.log:
        print(outcome.log, end="" if outcome.log.endswith("\n") else "\n")
    print(outcome.conclusion)
    append_job_summary(outcome.conclusion)
    return exit_code(outcome.verdict)
