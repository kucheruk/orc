#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocol for stream monitor — replaces duck typing / getattr across the codebase."""

from __future__ import annotations

from typing import Optional, Protocol

from .stream_monitor_state import MetricsStore


class ProcessProxy(Protocol):
    pid: Optional[int]
    returncode: Optional[int]

    def poll(self) -> Optional[int]: ...


class StreamMonitorProtocol(Protocol):
    """Typed contract for stream monitors used by supervisor, runner, and agent phases.

    StreamJsonMonitor implements this implicitly (structural subtyping).
    """

    proc: ProcessProxy
    metrics: MetricsStore
    last_output_time: float
    started_at: float
    init_pid: Optional[int]
    process_group_id: Optional[int]
    workdir: str
    run_token: str
    stderr_count: int
    last_stderr_line: str
    ui_followup_prompt: bool
    result_status: Optional[str]

    def maybe_report(self) -> None: ...
    def stop(self) -> None: ...
    def get_summary_text(self) -> str: ...
    def refresh_process_status(self) -> Optional[int]: ...
    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]: ...
    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]: ...
