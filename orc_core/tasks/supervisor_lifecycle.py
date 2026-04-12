#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

from .task_execution_types import TaskCompletionStatus
from ..log import log_event
from ..infra.io.debug_log import debug_log
from ..infra.monitoring.monitor_protocol import StreamMonitorProtocol
from ..infra.io.timeline import timeline_instant
from ..infra.process.process import is_pid_alive
from .supervisor_checks import (
    DEFAULT_CHECK_CHAIN,
    CompletionCheck,
    _task_done_in_backlog,
    _monitor_pid_missing,
)


class CompletionMonitor:
    """Monitors a running agent task and checks for various completion/failure conditions."""

    def __init__(
        self,
        task_path: Path,
        monitor: StreamMonitorProtocol,
        poll: float,
        stall_timeout: float,
        task_ttl: float,
        log_path: Path,
        nudge_after: int,
        nudge_cooldown: float,
        nudge_text: str,
        task_id: str,
        task_text: str,
        timeline_id: str = "",
        attempt: int = 0,
        elapsed_before_start: float = 0.0,
        ignore_initial_backlog_done: bool = False,
        escape_requested: Optional[Callable[[], bool]] = None,
        confirm_exit: Optional[Callable[[], bool]] = None,
        on_notify: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.task_path = task_path
        self.monitor = monitor
        self.poll = poll
        self.stall_timeout = stall_timeout
        self.task_ttl = task_ttl
        self.log_path = log_path
        self.nudge_after = nudge_after
        self.nudge_cooldown = nudge_cooldown
        self.nudge_text = nudge_text
        self.task_id = task_id
        self.task_text = task_text
        self.timeline_id = timeline_id
        self.attempt = attempt
        self.elapsed_before_start = elapsed_before_start
        self.ignore_initial_backlog_done = ignore_initial_backlog_done
        self.escape_requested = escape_requested
        self.confirm_exit = confirm_exit
        self.on_notify = on_notify

        self.start_time = time.time()
        self.pid_missing_since: Optional[float] = None
        self.last_heartbeat_time = 0.0
        self.last_tokens_value: Optional[int] = None
        self.last_tokens_time = time.time()
        self.last_stuck_notice_time = 0.0
        self.backlog_done_at_start = _task_done_in_backlog(task_path)

    # Chain of Responsibility: ordered check handlers (configurable via constructor)
    _CHECKS: tuple[CompletionCheck, ...] = DEFAULT_CHECK_CHAIN

    def check(self) -> Optional[TaskCompletionStatus]:
        """Run one iteration of checks. Returns a status if done, or None to continue."""
        for check_fn in self._CHECKS:
            result = check_fn(self)
            if result is not None:
                return result
        return None


def wait_for_completion(
    task_path: Path,
    monitor: StreamMonitorProtocol,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    nudge_after: int,
    nudge_cooldown: float,
    nudge_text: str,
    task_id: str,
    task_text: str,
    timeline_id: str = "",
    attempt: int = 0,
    elapsed_before_start: float = 0.0,
    ignore_initial_backlog_done: bool = False,
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
    on_notify: Optional[Callable[[str], None]] = None,
) -> TaskCompletionStatus:
    from ..notifications.notify import send_telegram_message as _default_notify
    _notify = on_notify or (lambda msg: _default_notify(msg, log_path))
    cm = CompletionMonitor(
        task_path=task_path,
        monitor=monitor,
        poll=poll,
        stall_timeout=stall_timeout,
        task_ttl=task_ttl,
        log_path=log_path,
        nudge_after=nudge_after,
        nudge_cooldown=nudge_cooldown,
        nudge_text=nudge_text,
        task_id=task_id,
        task_text=task_text,
        timeline_id=timeline_id,
        attempt=attempt,
        elapsed_before_start=elapsed_before_start,
        ignore_initial_backlog_done=ignore_initial_backlog_done,
        escape_requested=escape_requested,
        confirm_exit=confirm_exit,
        on_notify=_notify,
    )
    debug_log(
        "H3",
        "orc_core/supervisor_lifecycle.py:wait_for_completion:start",
        "wait loop start",
        {
            "task_path": str(task_path),
            "exists": task_path.exists(),
            "stall_timeout": stall_timeout,
            "task_ttl": task_ttl,
            "elapsed_before_start": elapsed_before_start,
            "poll": poll,
            "backlog_done_at_start": cm.backlog_done_at_start,
            "ignore_initial_backlog_done": ignore_initial_backlog_done,
        },
    )
    timeline_instant(
        timeline_id=timeline_id,
        task_id=task_id,
        step="wait_for_completion_loop",
        location="orc_core/supervisor_lifecycle.py:wait_for_completion",
        attempt=attempt,
        result="start",
        data={
            "poll_ms": int(max(poll, 0.2) * 1000),
            "stall_timeout_ms": int(stall_timeout * 1000),
            "task_ttl_ms": int(task_ttl * 1000),
            "elapsed_before_start_ms": int(elapsed_before_start * 1000),
        },
    )
    while True:
        result = cm.check()
        if result is not None:
            return result
        time.sleep(max(poll, 0.2))


def wait_for_process_exit(
    monitor: StreamMonitorProtocol,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    label: str,
    stop_on_followup_prompt: bool = False,
    timeline_id: str = "",
    task_id: str = "",
    attempt: int = 0,
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> TaskCompletionStatus:
    start_time = time.time()
    debug_log(
        "H3",
        "orc_core/supervisor_lifecycle.py:wait_for_process_exit:start",
        "wait process exit loop start",
        {
            "stall_timeout": stall_timeout,
            "task_ttl": task_ttl,
            "poll": poll,
            "label": label,
            "stop_on_followup_prompt": stop_on_followup_prompt,
        },
    )
    timeline_instant(
        timeline_id=timeline_id,
        task_id=task_id,
        step=f"{label}_wait_loop",
        location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
        attempt=attempt,
        result="start",
        data={"poll_ms": int(max(poll, 0.2) * 1000), "stall_timeout_ms": int(stall_timeout * 1000)},
    )
    while True:
        if escape_requested is not None and escape_requested():
            if confirm_exit is None or confirm_exit():
                log_event(log_path, "WARN", "escape interrupt confirmed", label=label)
                timeline_instant(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step=f"{label}_wait_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                    attempt=attempt,
                    result="interrupt",
                    reason="escape_confirmed",
                )
                raise KeyboardInterrupt
            log_event(log_path, "INFO", "escape interrupt cancelled", label=label)
        try:
            monitor.maybe_report()
        except Exception as exc:
            log_event(
                log_path,
                "ERROR",
                "phase monitor maybe_report crashed",
                label=label,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="process_exited",
                reason="maybe_report_exception",
            )
            return TaskCompletionStatus.PROCESS_EXITED
        if _monitor_pid_missing(monitor):
            log_event(log_path, "ERROR", "phase agent pid missing while still running", label=label)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="process_exited",
                reason="pid_missing",
            )
            return TaskCompletionStatus.PROCESS_EXITED
        if stop_on_followup_prompt and monitor.ui_followup_prompt:
            log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="waiting_for_input",
            )
            return TaskCompletionStatus.WAITING_FOR_INPUT
        if monitor.proc.poll() is not None:
            log_event(
                log_path,
                "INFO" if monitor.proc.returncode == 0 else "ERROR",
                "phase process exited",
                label=label,
                returncode=monitor.proc.returncode,
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="completed" if monitor.proc.returncode == 0 else "process_exited",
                data={"returncode": int(monitor.proc.returncode or 0)},
            )
            return TaskCompletionStatus.COMPLETED if monitor.proc.returncode == 0 else TaskCompletionStatus.PROCESS_EXITED
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", label=label, stall_seconds=stall_timeout)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="stalled",
                data={
                    "since_last_output_ms": int((time.time() - monitor.last_output_time) * 1000),
                    "stall_timeout_ms": int(stall_timeout * 1000),
                },
            )
            return TaskCompletionStatus.STALLED
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "phase ttl exceeded", label=label, task_ttl=task_ttl)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="ttl_exceeded",
                data={"task_ttl_ms": int(task_ttl * 1000)},
            )
            return TaskCompletionStatus.TTL_EXCEEDED
        time.sleep(max(poll, 0.2))


async def async_wait_for_completion(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_completion, **kwargs)


async def async_wait_for_process_exit(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_process_exit, **kwargs)
