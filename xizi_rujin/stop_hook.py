"""Claude Code / Codex 的 Stop 钩子。

stdin 是官方 Stop JSON。打回和无法判定都用 exit 0 + {"decision":"block"}，
不混用 exit 2，这样两边都认同一份输出。工具自己崩了就放行，并写 systemMessage。

文档：
https://code.claude.com/docs/en/hooks
https://developers.openai.com/codex/hooks
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

DEFAULT_MAX_BLOCKS = 3


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _fail_open(exc: BaseException) -> int:
    message = f"惜字如金 Stop 钩子自身出错，本次放行，避免卡死会话：{exc}"
    _emit({"systemMessage": message})
    print(message, file=sys.stderr)
    return 0


def _state_path(session_id: str) -> Path:
    root = os.environ.get("XIZI_STOP_HOOK_STATE_DIR")
    directory = Path(root) if root else Path(tempfile.gettempdir()) / "xizi-rujin-stop"
    directory.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session_id)[:80] or "default"
    return directory / f"{safe}.count"


def _blocks(session_id: str) -> int:
    path = _state_path(session_id)
    if not path.is_file():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def _record_block(session_id: str) -> None:
    path = _state_path(session_id)
    path.write_text(str(_blocks(session_id) + 1), encoding="utf-8")


def _max_blocks() -> int:
    raw = os.environ.get("XIZI_STOP_HOOK_MAX_BLOCKS", str(DEFAULT_MAX_BLOCKS))
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_BLOCKS
    return value if value >= 1 else 1


def _reason(verdict: str, conclusion: str) -> str:
    text = conclusion.strip() or verdict
    if verdict not in text:
        text = f"{verdict}：{text}"
    if len(text) > 500:
        text = text[:497] + "..."
    return text


def run_stop_hook() -> int:
    from xizi_rujin.audit_changed import ToolFailure, audit_changed

    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        return _fail_open(exc)
    if not isinstance(payload, dict):
        return _fail_open(RuntimeError("Stop 输入不是 JSON 对象"))
    event = payload.get("hook_event_name")
    if event not in (None, "Stop"):
        return 0
    # 官方示例：stop_hook_active 为真时立刻退出，避免钩子把自己再叫起来。
    if payload.get("stop_hook_active") is True:
        return 0
    tasks = payload.get("background_tasks") or []
    if isinstance(tasks, list) and tasks:
        return 0
    session_id = str(payload.get("session_id") or "default")
    if _blocks(session_id) >= _max_blocks():
        return 0
    cwd_text = payload.get("cwd") or os.getcwd()
    try:
        outcome = audit_changed(Path(str(cwd_text)), timeout=20)
    except ToolFailure as exc:
        message = f"惜字如金 Stop 钩子没法完成审计，本次放行：{exc}"
        _emit({"systemMessage": message})
        print(message, file=sys.stderr)
        return 0
    if outcome.verdict == "通过":
        return 0
    _record_block(session_id)
    _emit({"decision": "block", "reason": _reason(outcome.verdict, outcome.conclusion)})
    return 0


def main(argv: list[str] | None = None) -> int:
    del argv
    _configure_stdio()
    try:
        return run_stop_hook()
    except Exception as exc:
        return _fail_open(exc)
