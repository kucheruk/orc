#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resume state recovery and task file initialization for TaskExecutionEngine."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .request import TaskExecutionResult
    from .runtime import _ExecutionContext, _ResumeState

from ...observability import debug_log
from ...log import log_event
from ...agents.session.state import save_active_session, save_session_manifest
from ..integration.hooks import write_task_file
from ..ports import TaskStateWriter
from .request import TaskExecutionResult
from ..status import TaskExecutionStatus
from ..state import delete_runtime_state_file, read_task_active_seconds


def _default_writer() -> TaskStateWriter:
    from ...infra.io.task_state_adapter import DEFAULT_TASK_STATE_WRITER
    return DEFAULT_TASK_STATE_WRITER

_logger = logging.getLogger(__name__)


def recover_resume_state(
    log_path, ctx: _ExecutionContext, resume: _ResumeState,
) -> Optional[TaskExecutionResult]:
    """Recover state from existing task file. Updates ctx.task_id, ctx.task_text, resume fields."""
    request = ctx.request
    resume.resume_existing = request.task_path.exists()

    debug_log(
        "H2",
        "orc_core/task_execution.py:execute:task_state",
        "task file state",
        {"task_path": str(request.task_path), "exists": resume.resume_existing},
    )

    if not resume.resume_existing:
        return None

    try:
        active = json.loads(request.task_path.read_text(encoding="utf-8"))
        active_task_id = active.get("task_id")
        active_task_text = active.get("task_text")
        active_backlog_raw = str(active.get("backlog_path") or "").strip()
        raw_conversation_id = active.get("conversation_id", None)
        resume.resume_id = str(raw_conversation_id or "").strip() or None
        raw_restart_count = active.get("restart_count", 0)
        try:
            resume.persisted_restart_count = max(int(raw_restart_count), 0)
        except (TypeError, ValueError):
            resume.persisted_restart_count = 0
        resume.elapsed_before_start = read_task_active_seconds(request.task_path, expected_task_id=str(active_task_id or ""))
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        log_event(log_path, "ERROR", "failed to read task file", error=str(exc))
        _logger.warning(
            f"⚠️ Не удалось прочитать {request.task_path}. "
            "Исправь/удали файл состояния или запусти с --drop для чистого старта."
        )
        ctx.ts_exec.result = "continue"
        ctx.ts_exec.reason = "task_file_read_failed"
        return TaskExecutionResult(status=TaskExecutionStatus.CONTINUE, reason="task_file_read_failed", delay_seconds=max(request.timing.poll, 0.2))

    same_backlog = True
    if active_backlog_raw:
        try:
            same_backlog = Path(active_backlog_raw).resolve() == request.backlog_path.resolve()
        except (OSError, ValueError):
            same_backlog = active_backlog_raw == str(request.backlog_path)

    if not same_backlog:
        log_event(
            log_path,
            "WARN",
            "resume state ignored: backlog mismatch",
            task_backlog=active_backlog_raw,
            expected_backlog=str(request.backlog_path),
        )
        resume.resume_existing = False
        resume.resume_id = None
        resume.persisted_restart_count = 0
        resume.elapsed_before_start = 0.0

    if resume.resume_existing and active_task_id and request.task_path.exists():
        from ..backlog.source import MarkdownTaskSource

        if MarkdownTaskSource(ctx.base_backlog_path).is_task_done(active_task_id):
            log_event(log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
            _logger.info(f"✅ {active_task_id} уже отмечена [x]. Удаляю {request.task_path} и продолжаю.")
            try:
                request.task_path.unlink()
                delete_runtime_state_file(request.task_path, log_path, reason="stale_done_task_file")
            except OSError as exc:
                log_event(log_path, "ERROR", "failed to delete task file", error=str(exc))
            ctx.ts_exec.result = "continue"
            ctx.ts_exec.reason = "stale_done_task_file"
            return TaskExecutionResult(status=TaskExecutionStatus.CONTINUE, reason="stale_done_task_file")

    if resume.resume_existing:
        ctx.task_id = active_task_id or ctx.task_id
        ctx.task_text = active_task_text or ctx.task_text
        log_event(log_path, "INFO", "resume existing task", task_id=ctx.task_id)
        _logger.info(f"↩️ Обнаружена активная задача, запускаю resume для {ctx.task_id}.")
        if not resume.resume_id:
            log_event(
                log_path,
                "WARN",
                "task file has no conversation_id — auto-dropping for fresh start",
                task_id=ctx.task_id,
                restart_count=resume.persisted_restart_count,
            )
            _logger.info(f"🗑️ Стейт {ctx.task_id} без conversation_id — авто-сброс для чистого старта.")
            try:
                request.task_path.unlink()
                delete_runtime_state_file(request.task_path, log_path, reason="auto_drop_no_conversation")
            except OSError:
                pass
            resume.resume_existing = False
            resume.resume_id = None
            # Preserve restart_count so the agent knows it's a continuation
            resume.elapsed_before_start = 0.0
        log_event(
            log_path,
            "INFO",
            "resume selection",
            conversation_id=resume.resume_id or "",
            resume_from_latest=False,
            restart_count=resume.persisted_restart_count,
            active_seconds=resume.elapsed_before_start,
        )
    return None


def init_task_file(
    log_path, ctx: _ExecutionContext, resume: _ResumeState,
) -> None:
    """Create or enrich task file and persist session state."""
    request = ctx.request
    if not resume.resume_existing:
        write_task_file(
            request.base_workdir,
            request.task,
            request.backlog_path,
            log_path,
            restart_count=0,
            task_path_override=request.task_path,
        )
        if request.task_path.exists():
            try:
                payload = json.loads(request.task_path.read_text(encoding="utf-8"))
                if ctx.worktree_path_value:
                    payload["worktree_path"] = ctx.worktree_path_value
                payload["branch_name"] = str(payload.get("branch_name") or "")
                payload["status"] = "active"
                _default_writer().write_json(request.task_path, payload, ensure_ascii=False, indent=2)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                log_event(log_path, "WARN", "failed to enrich task state with worktree metadata", error=str(exc))
    if request.task_path.exists():
        try:
            session_payload = json.loads(request.task_path.read_text(encoding="utf-8"))
            save_active_session(
                request.base_workdir,
                {
                    "version": 1,
                    "task_id": str(session_payload.get("task_id") or ctx.task_id),
                    "session_id": str(session_payload.get("session_id") or ""),
                    "task_file": str(request.task_path),
                    "worktree_path": str(session_payload.get("worktree_path") or ctx.worktree_path_value),
                    "conversation_id": str(session_payload.get("conversation_id") or resume.resume_id or ""),
                    "status": "active",
                },
            )
            session_id = str(session_payload.get("session_id") or "").strip()
            if session_id:
                save_session_manifest(request.base_workdir, session_id, session_payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            log_event(log_path, "WARN", "failed to persist active session snapshot", error=str(exc))
