#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backlog invariant validation extracted from task_execution_finalize."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..log import log_event
from ..infra.io.debug_log import debug_log
from .execution.helpers import (
    _should_defer_base_backlog_sync_to_integration,
    _sync_done_task_from_runtime_to_base,
)
from .execution.request import TaskExecutionResult
from .execution.runtime import _ExecutionContext
from .task_status_types import TaskExecutionStatus

_logger = logging.getLogger(__name__)


def validate_backlog_invariant(
    engine,
    ctx: _ExecutionContext,
    current_task_id: str,
    base_backlog_path: Path,
    runtime_backlog_path: Path,
    ts_exec,
) -> Optional[TaskExecutionResult]:
    """Ensure base backlog reflects done state after completion. Returns failure result or None."""
    request = ctx.request
    try:
        from .task_source import MarkdownTaskSource

        base_done = MarkdownTaskSource(base_backlog_path).is_task_done(current_task_id)
        runtime_done = False
        if runtime_backlog_path != base_backlog_path:
            runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(current_task_id)
        if runtime_done and not base_done:
            if _should_defer_base_backlog_sync_to_integration(
                integrate_to_main=request.integrate_to_main,
                base_backlog_path=base_backlog_path,
                runtime_backlog_path=runtime_backlog_path,
            ):
                log_event(
                    engine.log_path,
                    "ERROR",
                    "backlog invariant violated after main integration: task marked done only in runtime worktree backlog",
                    task_id=current_task_id,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                    integrate_to_main=request.integrate_to_main,
                )
                debug_log(
                    "MI2",
                    "orc_core/task_execution.py:TaskExecutionEngine.execute",
                    "base backlog was not updated by integrated commit",
                    {
                        "task_id": current_task_id,
                        "base_backlog_path": str(base_backlog_path),
                        "runtime_backlog_path": str(runtime_backlog_path),
                    },
                )
                _logger.error(
                    "❌ После успешной main integration backlog в base не отмечен как done. "
                    "Значит, отметка попала не в task commit, а пыталась догнаться позже."
                )
                ts_exec.result = "failed"
                ts_exec.reason = "worktree_not_integrated_to_base"
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="worktree_not_integrated_to_base")
            synced = _sync_done_task_from_runtime_to_base(
                task_id=current_task_id,
                base_backlog_path=base_backlog_path,
                runtime_backlog_path=runtime_backlog_path,
                log_path=engine.log_path,
            )
            if not synced:
                log_event(
                    engine.log_path,
                    "WARN",
                    "backlog sync to base failed (likely race with concurrent integration); "
                    "integration step will reconcile",
                    task_id=current_task_id,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                )
    except (OSError, ValueError) as exc:
        log_event(
            engine.log_path,
            "ERROR",
            "failed to validate backlog invariant after completion",
            task_id=current_task_id,
            error=str(exc),
            base_backlog_path=str(base_backlog_path),
            runtime_backlog_path=str(runtime_backlog_path),
        )
    return None
