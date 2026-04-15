#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import uuid
from pathlib import Path
from typing import Optional, Tuple

from ..infra.io.atomic_io import write_json_atomic, write_text_atomic
from .task_dto import Task
from ..log import log_event, now_iso
from ..infra.io.state_paths import active_task_path
from .task_state import write_task_runtime_state


def _render_hook_script(template_path: Path, replacements: dict[str, str]) -> str:
    script = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        script = script.replace(key, value)
    return script


def _write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    write_text_atomic(path, content, encoding="utf-8")


def ensure_repo_hooks(workdir: str) -> Tuple[Path, Path]:
    cursor_dir = Path(workdir) / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    cursor_hooks_dir = cursor_dir / "hooks"
    cursor_hooks_dir.mkdir(parents=True, exist_ok=True)

    before_path = cursor_hooks_dir / "orc_before_submit.py"
    stop_path = cursor_hooks_dir / "orc_stop.py"
    hook_lib_path = cursor_hooks_dir / "orc_hook_lib.py"

    orc_root = Path(__file__).resolve().parents[2]
    hook_scripts_dir = orc_root / "orc_core" / "hook_scripts"
    replacements = {"__ORC_ROOT__": repr(str(orc_root))}
    before_script = _render_hook_script(hook_scripts_dir / "orc_before_submit.py", replacements)
    stop_script = _render_hook_script(hook_scripts_dir / "orc_stop.py", replacements)
    hook_lib_script = _render_hook_script(hook_scripts_dir / "orc_hook_lib.py", replacements)

    _write_if_changed(before_path, before_script)
    _write_if_changed(stop_path, stop_script)
    _write_if_changed(hook_lib_path, hook_lib_script)
    before_path.chmod(0o755)
    stop_path.chmod(0o755)
    hook_lib_path.chmod(0o755)
    return before_path, stop_path


def ensure_repo_hooks_config(workdir: str, before_path: Path, stop_path: Path, log_path: Path) -> Path:
    def _ensure_hooks_file(hooks_path: Path, before_cmd: str, stop_cmd: str, label: str) -> None:
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        if hooks_path.exists():
            try:
                data = json.loads(hooks_path.read_text(encoding="utf-8"))
            except Exception as exc:
                log_event(log_path, "ERROR", f"{label}: bad JSON", error=str(exc))
                data = {}
        else:
            data = {}
        data.setdefault("version", 1)
        hooks = data.setdefault("hooks", {})
        before_list = hooks.setdefault("beforeSubmitPrompt", [])
        stop_list = hooks.setdefault("stop", [])

        if not any(item.get("command") == before_cmd for item in before_list if isinstance(item, dict)):
            before_list.append({"command": before_cmd})
            log_event(log_path, "INFO", f"{label}: added beforeSubmitPrompt", command=before_cmd)
        if not any(item.get("command") == stop_cmd for item in stop_list if isinstance(item, dict)):
            stop_list.append({"command": stop_cmd})
            log_event(log_path, "INFO", f"{label}: added stop", command=stop_cmd)

        write_json_atomic(hooks_path, data, ensure_ascii=False, indent=2)

    cursor_dir = Path(workdir) / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    cursor_hooks_path = cursor_dir / "hooks.json"
    _ensure_hooks_file(
        cursor_hooks_path,
        f"python3 {before_path}",
        f"python3 {stop_path}",
        ".cursor/hooks.json",
    )
    return cursor_hooks_path


def write_task_file(
    workdir: str,
    task: Task,
    backlog_path: Path,
    log_path: Path,
    restart_count: int = 0,
    task_path_override: Optional[Path] = None,
) -> Path:
    task_path = task_path_override or active_task_path(workdir)
    task_path.parent.mkdir(parents=True, exist_ok=True)
    created_at = now_iso()
    payload = {
        "version": 1,
        "session_id": f"{task.task_id}-{uuid.uuid4().hex[:10]}",
        "task_id": task.task_id,
        "task_text": task.text,
        "backlog_path": str(backlog_path),
        "workspace_root": str(Path(workdir)),
        "state_root": str(task_path.parent),
        "conversation_id": "",
        "created_at": created_at,
        "restart_count": restart_count,
        "worktree_path": "",
        "branch_name": "",
        "status": "active",
    }
    write_json_atomic(task_path, payload, ensure_ascii=False, indent=2)
    write_task_runtime_state(task_path, task.task_id)
    log_event(log_path, "INFO", "task file written", path=str(task_path), task_id=task.task_id)
    return task_path


def update_task_restart_count(task_path: Path, log_path: Path, restart_count: int) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for restart update", error=str(exc))
        return
    payload["restart_count"] = restart_count
    try:
        write_json_atomic(task_path, payload, ensure_ascii=False, indent=2)
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update task restart count", error=str(exc))
        return


