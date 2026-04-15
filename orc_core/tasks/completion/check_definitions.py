#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared definitions for tasks.completion checks and lifecycle.

Holds `CompletionMonitor` data-holder and callable type aliases so that
`checks.py` and `lifecycle.py` both depend on this module instead of on
each other (breaks the checks ↔ lifecycle cycle).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from ..task_status import TaskCompletionStatus
from ...tasks.ports import StreamMonitorProtocol
from .ports import BacklogQueryPort, NotifyPort


CompletionCheck = Callable[["CompletionMonitor"], Optional[TaskCompletionStatus]]


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
        notify: NotifyPort,
        backlog_query: BacklogQueryPort,
        timeline_id: str = "",
        attempt: int = 0,
        elapsed_before_start: float = 0.0,
        ignore_initial_backlog_done: bool = False,
        escape_requested: Optional[Callable[[], bool]] = None,
        confirm_exit: Optional[Callable[[], bool]] = None,
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
        self.notify = notify
        self.backlog_query = backlog_query

        self.start_time = time.time()
        self.pid_missing_since: Optional[float] = None
        self.last_heartbeat_time = 0.0
        self.last_tokens_value: Optional[int] = None
        self.last_tokens_time = time.time()
        self.last_stuck_notice_time = 0.0
        self.backlog_done_at_start = backlog_query.is_task_done(task_path)
