#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-JSON monitor facade: wires collaborators and delegates every concern."""

import time
import uuid
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional

from ...infra.io.logging import log_event
from ...infra.process.agent_process import AgentProcess
from ...contracts.session import MonitorSnapshot
from .agent_output_sink import AgentOutputSink
from .conversation_persister import ConversationIdPersister
from .monitor_metrics_collector import MonitorMetricsCollector
from .orphan_tool_call_finalizer import OrphanedToolCallFinalizer
from .periodic_reporter import PeriodicReporter
from .snapshot_builder import SnapshotBuilder
from .stream_event_dispatcher import StreamEventDispatcher
from .stream_monitor_paths import StreamMonitorPaths
from .stream_monitor_state import StreamMonitorState


class StreamJsonMonitor:
    def __init__(
        self,
        agent_cmd: list[str],
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        workdir: str,
        agent_output_log_path: Optional[str] = None,
        child_env_overrides: Optional[Mapping[str, str]] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        timeline_id: str = "",
        attempt: int = 0,
        backlog_task_lister: Optional[Callable] = None,
        git_diff_fn: Optional[Callable] = None,
        state: Optional[StreamMonitorState] = None,
        collector: Optional[MonitorMetricsCollector] = None,
    ) -> None:
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.started_at = time.time()
        self.run_token = uuid.uuid4().hex
        self.timeline_id = str(timeline_id or "")
        self.attempt = max(int(attempt), 0)
        self.last_nudge_time = 0.0

        self._output_sink = AgentOutputSink(agent_output_log_path, task_id=task_id, log_path=log_path)
        self._state = state or StreamMonitorState(task_id=task_id, started_at=self.started_at, summary_lines=summary_lines)
        self.metrics = self._state.metrics

        self._paths = StreamMonitorPaths.resolve(workdir, child_env_overrides)
        self._conversation_persister = ConversationIdPersister(
            task_state_path=self._paths.task_state, task_id=task_id, log_path=log_path,
        )
        self._snapshot_builder = SnapshotBuilder(
            state=self._state, publisher=snapshot_publisher,
            timeline_id=self.timeline_id, task_id=task_id, attempt=self.attempt,
        )
        self._dispatcher = StreamEventDispatcher(
            state=self._state, output_sink=self._output_sink,
            conversation_persister=self._conversation_persister,
            log_path=log_path, task_id=task_id, timeline_id=self.timeline_id,
            attempt=self.attempt, started_at=self.started_at,
            snapshot_publisher=self._snapshot_builder.publish,
        )
        self._collector = collector or MonitorMetricsCollector(
            task_id=task_id, workdir=workdir, log_path=log_path, metrics=self.metrics,
            task_state_path=self._paths.task_state,
            task_runtime_state_path=self._paths.task_runtime_state,
            stats_path=self._paths.stats, metrics_path=self._paths.metrics,
            timeline_id=self.timeline_id, attempt=self.attempt, started_at=self.started_at,
            backlog_task_lister=backlog_task_lister, git_diff_fn=git_diff_fn,
        )
        self._reporter = PeriodicReporter(
            report_interval=report_interval, state=self._state, collector=self._collector,
            snapshot_builder=self._snapshot_builder, metrics=self.metrics, log_path=log_path,
            task_id=task_id, timeline_id=self.timeline_id, attempt=self.attempt,
        )
        self._orphan_finalizer = OrphanedToolCallFinalizer(
            state=self._state, snapshot_builder=self._snapshot_builder, log_path=log_path,
            task_id=task_id, timeline_id=self.timeline_id, attempt=self.attempt,
        )

        child_env = {str(k): str(v) for k, v in (child_env_overrides or {}).items()}
        self._agent = AgentProcess(
            agent_cmd=agent_cmd, workdir=workdir, log_path=log_path,
            child_env_overrides=child_env, run_token=self.run_token,
            on_stdout_line=self._dispatcher.on_stdout_line,
            on_stderr_line=self._dispatcher.on_stderr_line,
            on_process_exit=lambda rc: self._orphan_finalizer.handle_process_exit(
                reason=f"process_exit_rc_{rc}",
            ),
        )
        self.proc = self._agent.proc
        self.init_pid = self._agent.init_pid
        self.process_group_id = self._agent.process_group_id

    @property
    def stderr_count(self) -> int: return self._dispatcher.stderr_count
    @property
    def last_stderr_line(self) -> str: return self._dispatcher.last_stderr_line
    @property
    def status_only_reports(self) -> int: return self._dispatcher.status_only_reports
    @property
    def ui_followup_prompt(self) -> bool: return self._dispatcher.ui_followup_prompt
    @property
    def result_status(self) -> Optional[str]: return self._dispatcher.result_status
    @property
    def result_seen_at(self) -> Optional[float]: return self._dispatcher.result_seen_at
    @property
    def last_output_time(self) -> float: return self._agent.last_output_time
    @last_output_time.setter
    def last_output_time(self, value: float) -> None: self._agent.last_output_time = value
    @property
    def session_id(self) -> str | None: return self._state.session_id

    def set_progress(self, done: int, total: int, in_progress: int = 0) -> None:
        self._state.set_progress(done, total, in_progress)
        self._snapshot_builder.publish()

    def maybe_report(self) -> None:
        self._reporter.maybe_report()

    def get_summary_text(self) -> str:
        return self._state.summary_text()

    def send_keys(self, keys: Iterable[str], label: str = "") -> bool:
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        return False

    def refresh_process_status(self) -> int | None:
        return self._agent.refresh_status()

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]:
        result = self._state.force_finalize_live_tool_calls(reason)
        self._snapshot_builder.publish()
        return result

    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]:
        return self._state.active_tool_calls_watchdog_snapshot()

    def stop(self) -> None:
        self._agent.stop()
        self._output_sink.close()
