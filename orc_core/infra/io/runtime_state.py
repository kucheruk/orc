#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime state helpers: path computation, payload init/load for task runtime files."""

import json
from pathlib import Path

from ...log import log_event

TASK_RUNTIME_FILE_NAME = "orc-task-runtime.json"


def runtime_state_path(task_path: Path) -> Path:
    return task_path.with_name(TASK_RUNTIME_FILE_NAME)


def load_runtime_payload(runtime_path: Path) -> dict:
    try:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def init_runtime_payload(task_id: str) -> dict:
    return {
        "version": 1,
        "task_id": str(task_id or "").strip(),
        "active_seconds": 0.0,
        "last_heartbeat_at": 0.0,
        "run_id": "",
    }


def delete_runtime_state_file(task_path: Path, log_path: Path, reason: str) -> bool:
    runtime_path = runtime_state_path(task_path)
    if not runtime_path.exists():
        return False
    try:
        runtime_path.unlink()
        log_event(log_path, "WARN", "runtime state file removed", reason=reason, runtime_path=str(runtime_path))
        return True
    except Exception as exc:
        log_event(
            log_path,
            "ERROR",
            "failed to remove runtime state file",
            reason=reason,
            error=str(exc),
            runtime_path=str(runtime_path),
        )
        return False
