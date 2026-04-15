#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Optional

from ..log import log_event
from .ports import StatePathsPort, TaskStateWriter

TASK_RUNTIME_FILE_NAME = "orc-task-runtime.json"


def runtime_state_path(task_path: Path) -> Path:
    """Pure path computation — keeps callers free of infra.io."""
    return task_path.with_name(TASK_RUNTIME_FILE_NAME)


def create_temp_backlog(
    workdir: str,
    task_text: str,
    log_path: Path,
    *,
    paths: StatePathsPort,
) -> tuple[Path, str]:
    run_dir = paths.tmp_dir(workdir)
    run_dir.mkdir(parents=True, exist_ok=True)
    task_id = "ORC-SMOKE-001"
    backlog_path = run_dir / f"BACKLOG.temp.{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    normalized = " ".join(task_text.strip().split())
    backlog_path.write_text(f"- [ ] {task_id} {normalized}\n", encoding="utf-8")
    rel_backlog = str(backlog_path.relative_to(Path(workdir)))
    log_event(log_path, "INFO", "temporary backlog created", backlog_path=str(backlog_path), task_id=task_id)
    return backlog_path, rel_backlog


def load_task_payload(task_path: Path) -> dict:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_task_runtime_state(
    task_path: Path,
    task_id: str,
    *,
    writer: TaskStateWriter,
) -> Path:
    return writer.init_runtime_state(task_path, task_id)


def read_task_active_seconds(
    task_path: Path,
    *,
    writer: TaskStateWriter,
    expected_task_id: str = "",
) -> float:
    payload = writer.read_runtime_payload(task_path)
    if not payload:
        return 0.0
    task_id = str(expected_task_id or "").strip()
    payload_task_id = str(payload.get("task_id") or "").strip()
    if task_id and payload_task_id and payload_task_id != task_id:
        return 0.0
    try:
        return max(float(payload.get("active_seconds") or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def delete_task_file(
    task_path: Path,
    log_path: Path,
    reason: str,
    *,
    writer: TaskStateWriter,
    expected_task_id: Optional[str] = None,
    expected_backlog: Optional[Path] = None,
) -> bool:
    if not task_path.exists():
        return False
    payload = load_task_payload(task_path)
    if expected_task_id and str(payload.get("task_id") or "").strip() != expected_task_id:
        log_event(
            log_path,
            "WARN",
            "skip task file remove: task_id mismatch",
            reason=reason,
            expected_task_id=expected_task_id,
            actual_task_id=str(payload.get("task_id") or ""),
        )
        return False
    if expected_backlog is not None:
        actual_backlog = str(payload.get("backlog_path") or "").strip()
        if actual_backlog and Path(actual_backlog) != expected_backlog:
            log_event(
                log_path,
                "WARN",
                "skip task file remove: backlog mismatch",
                reason=reason,
                expected_backlog=str(expected_backlog),
                actual_backlog=actual_backlog,
            )
            return False
    try:
        task_path.unlink()
        log_event(log_path, "WARN", "task file removed", reason=reason, task_path=str(task_path))
        writer.delete_runtime_state(task_path, log_path, reason=f"{reason}:task_removed")
        return True
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to remove task file", reason=reason, error=str(exc), task_path=str(task_path))
        return False


def cleanup_stale_task_file(
    task_path: Path,
    log_path: Path,
    *,
    writer: TaskStateWriter,
    allowed_backlog: Optional[Path] = None,
) -> bool:
    if not task_path.exists():
        return False
    payload = load_task_payload(task_path)
    if not payload:
        return delete_task_file(task_path, log_path, reason="invalid_task_json", writer=writer)
    backlog_path_raw = str(payload.get("backlog_path") or "").strip()
    if not backlog_path_raw:
        return delete_task_file(task_path, log_path, reason="missing_backlog_path", writer=writer)
    backlog_path = Path(backlog_path_raw)
    if not backlog_path.exists():
        return delete_task_file(task_path, log_path, reason="backlog_missing", writer=writer)
    if allowed_backlog is not None and backlog_path.resolve() != allowed_backlog.resolve():
        log_event(
            log_path,
            "WARN",
            "task file references another backlog; keeping state",
            task_backlog=str(backlog_path),
            allowed_backlog=str(allowed_backlog),
        )
    return False


def update_task_conversation_id(
    task_path: Path,
    log_path: Path,
    conversation_id: str,
    *,
    writer: TaskStateWriter,
) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for conversation_id update", error=str(exc))
        return
    if payload.get("conversation_id") == conversation_id:
        return
    payload["conversation_id"] = conversation_id
    try:
        writer.write_json(task_path, payload, ensure_ascii=False, indent=2)
        log_event(log_path, "INFO", "stored conversation_id from agent ls", conversation_id=conversation_id)
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update conversation_id", error=str(exc))
