#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backlog completion detection: checks if a task was marked done in backlog files.

Extracted from TaskExecutionEngine to isolate the backlog-inspection concern
from the main stage execution loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..infra.io.debug_log import debug_log
from ..log import log_event
from .execution.helpers import (
    _should_defer_base_backlog_sync_to_integration,
    _sync_done_task_from_runtime_to_base,
)
from .execution.request import TaskExecutionResult
from .execution.runtime import _ExecutionContext
from ..models.task_status import TaskExecutionStatus
from .task_state import delete_runtime_state_file


def check_backlog_done(
    engine,
    ctx: _ExecutionContext,
    *,
    result: str,
    stage_id: str,
    stage_index: int,
    stage_is_final: bool,
    attempt_number: int,
    ts_attempt,
    tag: str,
    active_monitor,
    restart_count: int,
    missing_artifact_retry_budget: int,
) -> tuple[str, Optional[TaskExecutionResult], Optional[int], int]:
    """Check if task was marked done in backlog after non-completed monitor result.
    Returns (action, early_result, stage_next_index, updated_retry_budget).
    action: 'none' | 'return' | 'break'
    """
    request = ctx.request
    base_backlog_path = ctx.base_backlog_path
    runtime_backlog_path = ctx.runtime_backlog_path
    task_id = ctx.task_id
    task_text = ctx.task_text
    ts_exec = ctx.ts_exec

    # Kanban mode: _board sentinel is not a real backlog — skip done-detection
    if base_backlog_path.name == "_board" or base_backlog_path.is_dir():
        return "none", None, None, missing_artifact_retry_budget

    complete_kwargs = dict(
        current_task_id=task_id,
        current_task_text=task_text,
        current_tag=tag,
        current_monitor=active_monitor,
        current_stage_id=stage_id,
        current_stage_index=stage_index,
        current_stage_is_final=stage_is_final,
        current_attempt_number=attempt_number,
        current_ts_attempt=ts_attempt,
    )

    try:
        from .task_source import MarkdownTaskSource

        base_done = MarkdownTaskSource(base_backlog_path).is_task_done(task_id)
        runtime_done = False
        if runtime_backlog_path != base_backlog_path:
            runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(task_id)

        if base_done:
            log_event(
                engine.log_path,
                "WARN",
                "task marked done after non-completed monitor result",
                task_id=task_id,
                monitor_result=result,
            )
            action, early_result, next_idx, missing_artifact_retry_budget = _process_done_result(
                engine,
                ctx,
                complete_kwargs=complete_kwargs,
                completion_reason="base_backlog_marked_done",
                monitor_result=result,
                stage_id=stage_id,
                missing_artifact_retry_budget=missing_artifact_retry_budget,
                active_monitor=active_monitor,
                restart_count=restart_count,
                tag=tag,
                retry_log_msg="task marked done but stage artifact missing after process exit; retrying",
            )
            if action in ("return", "break"):
                return action, early_result, next_idx, missing_artifact_retry_budget

        if runtime_done:
            if _should_defer_base_backlog_sync_to_integration(
                integrate_to_main=request.integrate_to_main,
                base_backlog_path=base_backlog_path,
                runtime_backlog_path=runtime_backlog_path,
            ):
                log_event(
                    engine.log_path,
                    "INFO",
                    "runtime backlog marked done; deferring base backlog sync until main integration",
                    task_id=task_id,
                    monitor_result=result,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                )
                debug_log(
                    "MI3",
                    "orc_core/task_execution.py:TaskExecutionEngine.execute",
                    "deferred base backlog sync because runtime backlog done will be carried by task commit",
                    {
                        "task_id": task_id,
                        "monitor_result": result,
                        "base_backlog_path": str(base_backlog_path),
                        "runtime_backlog_path": str(runtime_backlog_path),
                    },
                )
            else:
                synced = _sync_done_task_from_runtime_to_base(
                    task_id=task_id,
                    base_backlog_path=base_backlog_path,
                    runtime_backlog_path=runtime_backlog_path,
                    log_path=engine.log_path,
                )
                if not synced:
                    log_event(
                        engine.log_path,
                        "ERROR",
                        "runtime backlog marked done but base backlog sync failed",
                        task_id=task_id,
                        base_backlog_path=str(base_backlog_path),
                        runtime_backlog_path=str(runtime_backlog_path),
                    )
                    ts_exec.result = "failed"
                    ts_exec.reason = "runtime_backlog_sync_failed"
                    return "return", TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="runtime_backlog_sync_failed"), None, missing_artifact_retry_budget
                log_event(
                    engine.log_path,
                    "WARN",
                    "task marked done in runtime worktree backlog after non-completed monitor result",
                    task_id=task_id,
                    monitor_result=result,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                )
            action, early_result, next_idx, missing_artifact_retry_budget = _process_done_result(
                engine,
                ctx,
                complete_kwargs=complete_kwargs,
                completion_reason="runtime_backlog_marked_done",
                monitor_result=result,
                stage_id=stage_id,
                missing_artifact_retry_budget=missing_artifact_retry_budget,
                active_monitor=active_monitor,
                restart_count=restart_count,
                tag=tag,
                retry_log_msg="runtime backlog marked done but stage artifact missing after process exit; retrying",
            )
            if action in ("return", "break"):
                return action, early_result, next_idx, missing_artifact_retry_budget

    except Exception as exc:
        log_event(
            engine.log_path,
            "ERROR",
            "failed to inspect backlog completion after non-completed monitor result",
            task_id=task_id,
            monitor_result=result,
            error=str(exc),
        )

    return "none", None, None, missing_artifact_retry_budget


def _process_done_result(
    engine,
    ctx: _ExecutionContext,
    *,
    complete_kwargs: dict,
    completion_reason: str,
    monitor_result: str,
    stage_id: str,
    missing_artifact_retry_budget: int,
    active_monitor,
    restart_count: int,
    tag: str,
    retry_log_msg: str,
) -> tuple[str, Optional[TaskExecutionResult], Optional[int], int]:
    """Process a done detection: validate stage, handle retry/finalize.
    Returns (action, result, stage_next_index, updated_retry_budget).
    action: 'return' | 'break' | 'retry'
    """
    from .task_agent_phases import should_retry_after_missing_stage_artifact
    from .execution.finalize import complete_stage, finalize_completed

    request = ctx.request
    task_id = ctx.task_id
    task_text = ctx.task_text

    stage_failure, stage_next_index, stage_completed_final = complete_stage(
        engine, ctx, **complete_kwargs, completion_reason=completion_reason,
    )
    if stage_failure is not None:
        if should_retry_after_missing_stage_artifact(
            stage_failure=stage_failure,
            monitor_result=monitor_result,
            current_stage_id=stage_id,
            retry_budget_left=missing_artifact_retry_budget,
        ):
            missing_artifact_retry_budget -= 1
            log_event(
                engine.log_path,
                "WARN",
                retry_log_msg,
                task_id=task_id,
                stage_id=stage_id,
                monitor_result=monitor_result,
                reason=stage_failure.reason,
                retry_budget_left=missing_artifact_retry_budget,
            )
            return "retry", None, None, missing_artifact_retry_budget
        return "return", stage_failure, None, missing_artifact_retry_budget

    if stage_completed_final and request.task_path.exists():
        try:
            request.task_path.unlink()
            delete_runtime_state_file(request.task_path, engine.log_path, reason=completion_reason)
        except OSError as exc:
            log_event(engine.log_path, "ERROR", "failed to delete task file", error=str(exc))
    if stage_completed_final:
        ctx.restart_count = restart_count
        finalize_result = finalize_completed(engine, ctx, task_id, task_text, tag, active_monitor)
        return "return", finalize_result, None, missing_artifact_retry_budget
    return "break", None, stage_next_index, missing_artifact_retry_budget
