"""把 Stop 钩子合并进 Claude Code 或 Codex 的配置。已有字段保留，不整文件覆盖。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HOOK_TIMEOUT = 120


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def hook_command(launcher: Path | None = None) -> dict:
    """exec 形式：command 是 python 可执行文件，参数分开传，Windows 上不经 shell。"""
    if launcher is None:
        candidate = Path(__file__).resolve().parents[1] / "xizi_rujin.py"
        launcher = candidate if candidate.is_file() else None
    if launcher is not None:
        args = [str(launcher), "hook-stop"]
    else:
        args = ["-m", "xizi_rujin", "hook-stop"]
    return {
        "type": "command",
        "command": sys.executable,
        "args": args,
        "timeout": HOOK_TIMEOUT,
    }


def settings_path(scope: str, harness: str, project: Path, home: Path) -> Path:
    if harness == "claude":
        base = home / ".claude" if scope == "user" else project / ".claude"
        return base / "settings.json"
    if harness == "codex":
        base = home / ".codex" if scope == "user" else project / ".codex"
        return base / "hooks.json"
    raise ValueError(f"未知 harness：{harness}")


def _home() -> Path:
    for key in ("HOME", "USERPROFILE"):
        value = os.environ.get(key)
        if value:
            return Path(value)
    return Path.home()


def load_settings(path: Path) -> tuple[dict | None, str | None]:
    """读配置。文件不存在给空对象；JSON 坏了返回错误，调用方不得写入。"""
    if not path.exists():
        return {}, None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, f"不是合法 JSON，拒绝覆盖：{path}"
    if not isinstance(data, dict):
        return None, f"配置不是 JSON 对象，拒绝覆盖：{path}"
    return data, None


def _is_ours(hook: dict) -> bool:
    parts = [str(hook.get("command", ""))]
    args = hook.get("args") or []
    if isinstance(args, list):
        parts.extend(str(item) for item in args)
    return "hook-stop" in " ".join(parts)


def install_into(data: dict, launcher: Path | None = None) -> str | None:
    hooks = data.get("hooks")
    if hooks is None:
        hooks = {}
        data["hooks"] = hooks
    if not isinstance(hooks, dict):
        return "hooks 字段不是对象，拒绝覆盖"
    stop = hooks.get("Stop")
    if stop is None:
        stop = []
        hooks["Stop"] = stop
    if not isinstance(stop, list):
        return "Stop 字段不是数组，拒绝覆盖"
    for group in stop:
        if not isinstance(group, dict):
            continue
        inner = group.get("hooks") or []
        if isinstance(inner, list) and any(isinstance(item, dict) and _is_ours(item) for item in inner):
            return None
    stop.append({"hooks": [hook_command(launcher)]})
    return None


def uninstall_from(data: dict) -> None:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return
    stop = hooks.get("Stop")
    if not isinstance(stop, list):
        return
    kept: list = []
    for group in stop:
        if not isinstance(group, dict):
            kept.append(group)
            continue
        inner = group.get("hooks") or []
        if not isinstance(inner, list):
            kept.append(group)
            continue
        remaining = [item for item in inner if not (isinstance(item, dict) and _is_ours(item))]
        if not remaining:
            continue
        updated = dict(group)
        updated["hooks"] = remaining
        kept.append(updated)
    if kept:
        hooks["Stop"] = kept
    else:
        hooks.pop("Stop", None)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _harnesses(name: str) -> list[str]:
    if name == "both":
        return ["claude", "codex"]
    return [name]


def _run(argv: list[str], *, remove: bool) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", required=True, choices=["project", "user"])
    parser.add_argument("--harness", default="both", choices=["claude", "codex", "both"])
    parser.add_argument("--project", default=None)
    parser.add_argument("--launcher", default=None)
    args = parser.parse_args(argv)
    project = Path(args.project) if args.project else Path.cwd()
    home = _home()
    launcher = Path(args.launcher) if args.launcher else None
    for harness in _harnesses(args.harness):
        path = settings_path(args.scope, harness, project, home)
        data, error = load_settings(path)
        if error or data is None:
            print(error or "拒绝覆盖", file=sys.stderr)
            return 2
        if remove:
            uninstall_from(data)
        else:
            problem = install_into(data, launcher)
            if problem:
                print(problem, file=sys.stderr)
                return 2
        _write(path, data)
        print(f"已写入 {path}")
    return 0


def main(argv: list[str] | None = None, *, remove: bool = False) -> int:
    _configure_stdio()
    if argv is None:
        argv = sys.argv[1:]
    return _run(argv, remove=remove)
