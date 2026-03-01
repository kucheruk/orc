#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

from .backlog_status import inspect_backlog


def resumable_task_id(task_path: Path, backlog_path: Path) -> str:
    if not task_path.exists() or not backlog_path.exists():
        return ""
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    task_id = str(payload.get("task_id") or "").strip()
    conversation_id = str(payload.get("conversation_id") or "").strip()
    payload_backlog = str(payload.get("backlog_path") or "").strip()
    if not task_id or not conversation_id or not payload_backlog:
        return ""
    try:
        same_backlog = Path(payload_backlog).resolve() == backlog_path.resolve()
    except Exception:
        same_backlog = payload_backlog == str(backlog_path)
    if not same_backlog:
        return ""
    status = inspect_backlog(backlog_path)
    for task in status.open_tasks:
        if task.task_id == task_id:
            return task_id
    return ""
