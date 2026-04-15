#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

from ..tasks.task_status_types import TaskCompletionStatus
from ..log import log_event
from ..infra.io.debug_log import debug_log
from ..infra.monitoring.monitor_protocol import StreamMonitorProtocol
from ..infra.io.timeline import timeline_instant
from ..infra.process.process import is_pid_alive
from .check_definitions import CompletionMonitor
from .checks import DEFAULT_CHECK_CHAIN
from .check_queries import _monitor_pid_missing
from .ports import BacklogQueryPort, NotifyPort


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
    notify: NotifyPort,
    backlog_query: BacklogQueryPort,
    timeline_id: str = "",
    attempt: int = 0,
    elapsed_before_start: float = 0.0,
    ignore_initial_backlog_done: bool = False,
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> TaskCompletionStatus:
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
        notify=notify,
        backlog_query=backlog_query,
        timeline_id=timeline_id,
        attempt=attempt,
        elapsed_before_start=elapsed_before_start,
        ignore_initial_backlog_done=ignore_initial_backlog_done,
        escape_requested=escape_requested,
        confirm_exit=confirm_exit,
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
        for check_fn in DEFAULT_CHECK_CHAIN:
            result = check_fn(cm)
            if result is not None:
                return result
        time.sleep(max(poll, 0.2))


class ProcessExitMonitor:
    """Monitors an agent phase (commit, pre-check) for process exit.

    Simpler than CompletionMonitor: no task file, no backlog checks.
    Uses the same Chain of Responsibility pattern.
    """

    def __init__(
        self,
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
    ) -> None:
        self.monitor = monitor
        self.poll = poll
        self.stall_timeout = stall_timeout
        self.task_ttl = task_ttl
        self.log_path = log_path
        self.label = label
        self.stop_on_followup_prompt = stop_on_followup_prompt
        self.timeline_id = timeline_id
        self.task_id = task_id
        self.attempt = attempt
        self.escape_requested = escape_requested
        self.confirm_exit = confirm_exit
        self.start_time = time.time()

    def check(self) -> Optional[TaskCompletionStatus]:
        for check_fn in _PROCESS_EXIT_CHECKS:
            result = check_fn(self)
            if result is not None:
                return result
        return None


def _pe_check_escape(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    if pm.escape_requested is not None and pm.escape_requested():
        if pm.confirm_exit is None or pm.confirm_exit():
            log_event(pm.log_path, "WARN", "escape interrupt confirmed", label=pm.label)
            timeline_instant(
                timeline_id=pm.timeline_id, task_id=pm.task_id,
                step=f"{pm.label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=pm.attempt, result="interrupt", reason="escape_confirmed",
            )
            raise KeyboardInterrupt
        log_event(pm.log_path, "INFO", "escape interrupt cancelled", label=pm.label)
    return None


def _pe_check_report(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    try:
        pm.monitor.maybe_report()
    except Exception as exc:
        log_event(
            pm.log_path, "ERROR", "phase monitor maybe_report crashed",
            label=pm.label, error=str(exc), exception_type=type(exc).__name__,
        )
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt, result="process_exited", reason="maybe_report_exception",
        )
        return TaskCompletionStatus.PROCESS_EXITED
    return None


def _pe_check_pid_missing(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    if _monitor_pid_missing(pm.monitor):
        log_event(pm.log_path, "ERROR", "phase agent pid missing while still running", label=pm.label)
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt, result="process_exited", reason="pid_missing",
        )
        return TaskCompletionStatus.PROCESS_EXITED
    return None


def _pe_check_followup(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    if pm.stop_on_followup_prompt and pm.monitor.ui_followup_prompt:
        log_event(pm.log_path, "WARN", "follow-up prompt visible during phase", label=pm.label)
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt, result="waiting_for_input",
        )
        return TaskCompletionStatus.WAITING_FOR_INPUT
    return None


def _pe_check_process_exited(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    if pm.monitor.proc.poll() is not None:
        rc = int(pm.monitor.proc.returncode or 0)
        log_event(
            pm.log_path, "INFO" if rc == 0 else "ERROR",
            "phase process exited", label=pm.label, returncode=rc,
        )
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt,
            result="completed" if rc == 0 else "process_exited",
            data={"returncode": rc},
        )
        return TaskCompletionStatus.COMPLETED if rc == 0 else TaskCompletionStatus.PROCESS_EXITED
    return None


def _pe_check_stall(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    silence = time.time() - pm.monitor.last_output_time
    if silence > pm.stall_timeout:
        log_event(pm.log_path, "ERROR", "stall detected", label=pm.label, stall_seconds=pm.stall_timeout)
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt, result="stalled",
            data={"since_last_output_ms": int(silence * 1000), "stall_timeout_ms": int(pm.stall_timeout * 1000)},
        )
        return TaskCompletionStatus.STALLED
    return None


def _pe_check_ttl(pm: ProcessExitMonitor) -> Optional[TaskCompletionStatus]:
    elapsed = time.time() - pm.start_time
    if elapsed > pm.task_ttl:
        log_event(pm.log_path, "ERROR", "phase ttl exceeded", label=pm.label, task_ttl=pm.task_ttl)
        timeline_instant(
            timeline_id=pm.timeline_id, task_id=pm.task_id,
            step=f"{pm.label}_wait_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
            attempt=pm.attempt, result="ttl_exceeded",
            data={"task_ttl_ms": int(pm.task_ttl * 1000)},
        )
        return TaskCompletionStatus.TTL_EXCEEDED
    return None


ProcessExitCheck = Callable[["ProcessExitMonitor"], Optional[TaskCompletionStatus]]

_PROCESS_EXIT_CHECKS: tuple[ProcessExitCheck, ...] = (
    _pe_check_escape,
    _pe_check_report,
    _pe_check_pid_missing,
    _pe_check_followup,
    _pe_check_process_exited,
    _pe_check_stall,
    _pe_check_ttl,
)


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
    pm = ProcessExitMonitor(
        monitor=monitor, poll=poll, stall_timeout=stall_timeout,
        task_ttl=task_ttl, log_path=log_path, label=label,
        stop_on_followup_prompt=stop_on_followup_prompt,
        timeline_id=timeline_id, task_id=task_id, attempt=attempt,
        escape_requested=escape_requested, confirm_exit=confirm_exit,
    )
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
        timeline_id=timeline_id, task_id=task_id,
        step=f"{label}_wait_loop",
        location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
        attempt=attempt, result="start",
        data={"poll_ms": int(max(poll, 0.2) * 1000), "stall_timeout_ms": int(stall_timeout * 1000)},
    )
    while True:
        result = pm.check()
        if result is not None:
            return result
        time.sleep(max(poll, 0.2))


async def async_wait_for_completion(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_completion, **kwargs)


async def async_wait_for_process_exit(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_process_exit, **kwargs)
