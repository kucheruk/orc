#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocols for stream monitor — split by consumer need (ISP)."""

from __future__ import annotations

from typing import Optional, Protocol

from .monitor_dto import MetricsStore


class ProcessProxy(Protocol):
    pid: Optional[int]
    returncode: Optional[int]

    def poll(self) -> Optional[int]: ...


class MonitorMetrics(Protocol):
    """Metrics and stderr tracking — used by status displays and diagnostics."""

    metrics: MetricsStore
    stderr_count: int
    last_stderr_line: str


class MonitorLifecycle(Protocol):
    """Process lifecycle — used by supervisor to manage the agent process."""

    proc: ProcessProxy
    init_pid: Optional[int]
    process_group_id: Optional[int]

    def stop(self) -> None: ...
    def refresh_process_status(self) -> Optional[int]: ...


class ToolCallManager(Protocol):
    """Active tool call management — used by watchdog and stall detection."""

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]: ...
    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]: ...


class StreamMonitorProtocol(
    MonitorMetrics,
    MonitorLifecycle,
    ToolCallManager,
    Protocol,
):
    """Full contract for stream monitors — composes smaller protocols.

    StreamJsonMonitor implements this implicitly (structural subtyping).
    Consumers should depend on the smallest protocol they need.
    """

    last_output_time: float
    started_at: float
    workdir: str
    run_token: str
    ui_followup_prompt: bool
    result_status: Optional[str]

    def maybe_report(self) -> None: ...
    def get_summary_text(self) -> str: ...
