#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent task state file (`active-task.json`) for a single agent session.

Split from the now-deleted `hooks.py` — what remains here is the runtime-state
bookkeeping ORC needs regardless of whether any external hook is installed.
"""

import json
import uuid
from pathlib import Path
from typing import Optional

from ..dto import Task
from ...log import log_event, now_iso
from ..ports import StatePathsPort, TaskStateWriter
from ..state import write_task_runtime_state


def write_task_file(
    workdir: str,
    task: Task,
    backlog_path: Path,
    log_path: Path,
    *,
    writer: TaskStateWriter,
    paths: StatePathsPort,
    restart_count: int = 0,
    task_path_override: Optional[Path] = None,
) -> Path:
    task_path = task_path_override or paths.active_task(workdir)
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
    writer.write_json(task_path, payload, ensure_ascii=False, indent=2)
    write_task_runtime_state(task_path, task.task_id, writer=writer)
    log_event(log_path, "INFO", "task file written", path=str(task_path), task_id=task.task_id)
    return task_path


def update_task_restart_count(
    task_path: Path,
    log_path: Path,
    restart_count: int,
    *,
    writer: TaskStateWriter,
) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for restart update", error=str(exc))
        return
    payload["restart_count"] = restart_count
    try:
        writer.write_json(task_path, payload, ensure_ascii=False, indent=2)
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update task restart count", error=str(exc))
        return
