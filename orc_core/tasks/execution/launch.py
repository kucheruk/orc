#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent launch and wait — extracted from TaskExecutionEngine."""

from __future__ import annotations

from ...infra.io.debug_log import debug_log
from ...infra.io.timeline import timeline_step
from ...quit_signal import is_stop_requested
from ...supervision.lifecycle import wait_for_completion
from ..task_agent_phases import cleanup_monitor_processes
from .request import LaunchConfig
from .runtime import _ExecutionContext
from ..task_status_types import TaskCompletionStatus


def launch_and_wait(
    worker,
    ctx: _ExecutionContext,
    launch_config: LaunchConfig,
    log_path,
    *,
    elapsed_before_start: float,
    ignore_initial_backlog_done: bool,
    attempt_number: int,
) -> tuple[object, TaskCompletionStatus]:
    """Launch agent, wait for completion, cleanup. Returns (monitor, status)."""
    request = ctx.request
    active_monitor = worker.launch(launch_config)
    try:
        with timeline_step(
            timeline_id=ctx.timeline_id,
            task_id=ctx.task_id,
            step="wait_for_completion",
            location="orc_core/task_execution.py:launch_and_wait",
            attempt=attempt_number,
        ) as ts_wait:
            result = wait_for_completion(
                task_path=request.task_path,
                monitor=active_monitor,
                poll=request.timing.poll,
                stall_timeout=request.timing.stall_timeout,
                task_ttl=request.timing.task_ttl,
                elapsed_before_start=elapsed_before_start,
                ignore_initial_backlog_done=ignore_initial_backlog_done,
                log_path=log_path,
                nudge_after=request.timing.nudge_after,
                nudge_cooldown=request.timing.nudge_cooldown,
                nudge_text=request.timing.nudge_text,
                task_id=ctx.task_id,
                task_text=ctx.task_text,
                timeline_id=ctx.timeline_id,
                attempt=attempt_number,
                escape_requested=is_stop_requested,
            )
            ts_wait.result = result
    finally:
        try:
            active_monitor.stop()
        except Exception:
            pass
        cleanup_monitor_processes(active_monitor, log_path, label="agent")
    debug_log(
        "H8",
        "orc_core/task_execution.py:execute:completion_state",
        "completion state",
        {
            "result": result,
            "monitor_is_none": active_monitor is None,
            "lines": active_monitor.metrics.total_lines if active_monitor else -1,
            "commands": active_monitor.metrics.command_count if active_monitor else -1,
            "tokens_total": (active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-") if active_monitor else "-",
        },
    )
    return active_monitor, result
