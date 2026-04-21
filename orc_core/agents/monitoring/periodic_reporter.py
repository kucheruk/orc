#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PeriodicReporter — owns the report cadence and orchestrates one report cycle.

Responsibilities:
  - throttle reports by ``report_interval`` seconds
  - drive the MonitorMetricsCollector refresh sequence
  - tick the spinner and publish a snapshot via SnapshotBuilder
  - emit timeline entries (live-status change + report-duration) and write the
    periodic "stats report" log line
"""

from __future__ import annotations

import time
from pathlib import Path

from ...log import log_event, now_ms
from ...infra.io.timeline import timeline_instant
from ...contracts.session import MetricsStore
from .monitor_metrics_collector import MonitorMetricsCollector
from .snapshot_builder import SnapshotBuilder
from .stream_monitor_state import StreamMonitorState


class PeriodicReporter:
    def __init__(
        self,
        *,
        report_interval: float,
        state: StreamMonitorState,
        collector: MonitorMetricsCollector,
        snapshot_builder: SnapshotBuilder,
        metrics: MetricsStore,
        log_path: Path,
        task_id: str,
        timeline_id: str,
        attempt: int,
    ) -> None:
        self._interval = max(report_interval, 1.0)
        self._state = state
        self._collector = collector
        self._snapshot_builder = snapshot_builder
        self._metrics = metrics
        self._log_path = log_path
        self._task_id = task_id
        self._timeline_id = timeline_id
        self._attempt = attempt
        self._last_report_time = 0.0

    def maybe_report(self) -> None:
        now = time.time()
        if now - self._last_report_time < self._interval:
            return
        self._last_report_time = now

        started_ms = now_ms()
        self._collector.refresh_backlog_progress(self._state)
        self._collector.maybe_update_git_stats(now)
        self._collector.update_task_runtime_state()
        self._collector.update_eta_forecast(self._state)
        self._collector.write_metrics_snapshot()
        self._state.tick_spinner()
        snapshot = self._snapshot_builder.publish()
        self._snapshot_builder.emit_live_status_change(snapshot)

        log_event(
            self._log_path,
            "INFO",
            "stats report",
            tokens=self._metrics.tokens_total if self._metrics.tokens_total is not None else "-",
            lines=self._metrics.total_lines,
            commands=self._metrics.command_count,
            files_edited=self._metrics.files_edited if self._metrics.files_edited is not None else "-",
        )
        timeline_instant(
            timeline_id=self._timeline_id,
            task_id=self._task_id,
            step="monitor_maybe_report",
            location="orc_core/agents/monitoring/periodic_reporter.py:PeriodicReporter.maybe_report",
            attempt=self._attempt,
            result="reported",
            data={"duration_ms": max(now_ms() - started_ms, 0)},
        )
