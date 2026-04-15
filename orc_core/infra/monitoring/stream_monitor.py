#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-JSON monitor coordinator: delegates to dedicated collaborators for paths, event dispatch,
process lifecycle, metrics, and conversation persistence."""

import time
import uuid
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional

from ..io.logging import log_event, now_ms
from ..io.timeline import timeline_instant
from ..process.agent_process import AgentProcess
from .agent_output_sink import AgentOutputSink
from .conversation_persister import ConversationIdPersister
from .monitor_metrics_collector import MonitorMetricsCollector
from .stream_event_dispatcher import StreamEventDispatcher
from .stream_monitor_paths import StreamMonitorPaths

from ...tasks.ports import MonitorSnapshot
from .stream_monitor_state import StreamMonitorState

GIT_STATS_TIMEOUT_SECONDS = 10.0


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
        state: Optional["StreamMonitorState"] = None,
        collector: Optional["MonitorMetricsCollector"] = None,
    ) -> None:
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.started_at = time.time()
        self.run_token = uuid.uuid4().hex
        self.timeline_id = str(timeline_id or "")
        self.attempt = max(int(attempt), 0)
        self.last_nudge_time = 0.0
        self._snapshot_publisher = snapshot_publisher
        self._output_sink = AgentOutputSink(
            agent_output_log_path,
            task_id=task_id,
            log_path=log_path,
        )

        self._state = state or StreamMonitorState(task_id=task_id, started_at=self.started_at, summary_lines=summary_lines)
        self.metrics = self._state.metrics
        self._report_interval = max(report_interval, 1.0)
        self._last_report_time = 0.0

        self._paths = StreamMonitorPaths.resolve(workdir, child_env_overrides)
        self._conversation_persister = ConversationIdPersister(
            task_state_path=self._paths.task_state,
            task_id=task_id,
            log_path=log_path,
        )
        self._dispatcher = StreamEventDispatcher(
            state=self._state,
            output_sink=self._output_sink,
            conversation_persister=self._conversation_persister,
            log_path=log_path,
            task_id=task_id,
            timeline_id=self.timeline_id,
            attempt=self.attempt,
            started_at=self.started_at,
            snapshot_publisher=self._publish_snapshot,
        )
        self._last_live_status_marker: tuple[str, str, int, bool] | None = None
        self._collector = collector or MonitorMetricsCollector(
            task_id=task_id, workdir=workdir, log_path=log_path,
            metrics=self.metrics,
            task_state_path=self._paths.task_state,
            task_runtime_state_path=self._paths.task_runtime_state,
            stats_path=self._paths.stats, metrics_path=self._paths.metrics,
            timeline_id=self.timeline_id, attempt=self.attempt,
            started_at=self.started_at,
            backlog_task_lister=backlog_task_lister,
            git_diff_fn=git_diff_fn,
        )

        child_env = {str(k): str(v) for k, v in (child_env_overrides or {}).items()}
        # Spawn agent subprocess — callbacks run on the asyncio reader thread
        self._agent = AgentProcess(
            agent_cmd=agent_cmd,
            workdir=workdir,
            log_path=log_path,
            child_env_overrides=child_env,
            run_token=self.run_token,
            on_stdout_line=self._dispatcher.on_stdout_line,
            on_stderr_line=self._dispatcher.on_stderr_line,
            on_process_exit=lambda rc: self._finalize_orphaned_tool_calls_on_process_exit(
                reason=f"process_exit_rc_{rc}",
            ),
        )
        # Expose process proxy for compatibility
        self.proc = self._agent.proc
        self.init_pid = self._agent.init_pid
        self.process_group_id = self._agent.process_group_id

    # ── Delegated event-derived attributes (preserve public surface) ─

    @property
    def stderr_count(self) -> int:
        return self._dispatcher.stderr_count

    @property
    def last_stderr_line(self) -> str:
        return self._dispatcher.last_stderr_line

    @property
    def status_only_reports(self) -> int:
        return self._dispatcher.status_only_reports

    @property
    def ui_followup_prompt(self) -> bool:
        return self._dispatcher.ui_followup_prompt

    @property
    def result_status(self) -> Optional[str]:
        return self._dispatcher.result_status

    @property
    def result_seen_at(self) -> Optional[float]:
        return self._dispatcher.result_seen_at

    @property
    def last_output_time(self) -> float:
        return self._agent.last_output_time

    @last_output_time.setter
    def last_output_time(self, value: float) -> None:
        self._agent.last_output_time = value

    @property
    def session_id(self) -> str | None:
        return self._state.session_id

    def set_progress(self, done: int, total: int, in_progress: int = 0) -> None:
        self._state.set_progress(done, total, in_progress)
        self._publish_snapshot()

    # Backward-compatible wrappers for tests/helpers.
    def _append_reasoning_fragment(self, fragment: str) -> None:
        self._state.append_reasoning_fragment(fragment)

    def _remember_reasoning(self, event: Dict[str, object], text: str) -> None:
        self._state._remember_reasoning(event, text)

    def _reasoning_lines_for_panel(self, max_width: int = 90, max_lines: int = 5) -> list[str]:
        return self._state.reasoning_lines_for_panel(max_width=max_width, max_lines=max_lines)

    def _summarize_event(self, event: Dict[str, object], text: str) -> str:
        return self._state._summarize_event(event, text)

    # ── Periodic reporting (delegated to MonitorMetricsCollector) ─

    def maybe_report(self) -> None:
        started_ms = now_ms()
        now = time.time()
        if now - self._last_report_time < self._report_interval:
            return
        self._last_report_time = now
        self._collector.refresh_backlog_progress(self._state)
        self._collector.maybe_update_git_stats(now)
        self._collector.update_task_runtime_state()
        self._collector.update_eta_forecast(self._state)
        self._collector.write_metrics_snapshot()
        self._state.tick_spinner()
        self._publish_snapshot()
        live_snapshot = self._state.build_snapshot()
        live_marker = (
            str(getattr(live_snapshot, "live_phase", "")),
            str(getattr(live_snapshot, "live_status", "")),
            int(getattr(live_snapshot, "active_tool_call_count", 0)),
            bool(getattr(live_snapshot, "is_subagent_activity", False)),
        )
        if live_marker != self._last_live_status_marker:
            self._last_live_status_marker = live_marker
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="live_status_update",
                location="orc_core/stream_monitor.py:StreamJsonMonitor.maybe_report",
                attempt=self.attempt,
                result=live_marker[0],
                data={
                    "status": live_marker[1],
                    "active_tool_calls": live_marker[2],
                    "is_subagent_activity": live_marker[3],
                },
            )
        log_event(
            self.log_path,
            "INFO",
            "stats report",
            tokens=self.metrics.tokens_total if self.metrics.tokens_total is not None else "-",
            lines=self.metrics.total_lines,
            commands=self.metrics.command_count,
            files_edited=self.metrics.files_edited if self.metrics.files_edited is not None else "-",
        )
        timeline_instant(
            timeline_id=self.timeline_id,
            task_id=self.task_id,
            step="monitor_maybe_report",
            location="orc_core/stream_monitor.py:StreamJsonMonitor.maybe_report",
            attempt=self.attempt,
            result="reported",
            data={"duration_ms": max(now_ms() - started_ms, 0)},
        )

    # ── Public API ──────────────────────────────────────────────

    def get_summary_text(self) -> str:
        return self._state.summary_text()

    def send_keys(self, keys: Iterable[str], label: str = "") -> bool:
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        return False

    def refresh_process_status(self) -> int | None:
        return self._agent.refresh_status()

    def _finalize_orphaned_tool_calls_on_process_exit(self, reason: str) -> None:
        try:
            result = self._state.force_finalize_live_tool_calls(reason)
        except Exception as exc:
            log_event(self.log_path, "WARN", "forced_tool_close_failed", reason=reason, error=str(exc))
            return
        cleared = int(result.get("cleared") or 0)
        if cleared <= 0:
            return
        pending = result.get("pending")
        log_event(
            self.log_path, "WARN", "forced_tool_close",
            reason=str(result.get("reason") or reason),
            cleared=cleared,
            pending_preview=pending if isinstance(pending, list) else [],
        )
        timeline_instant(
            timeline_id=self.timeline_id,
            task_id=self.task_id,
            step="forced_tool_close",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._finalize_orphaned_tool_calls_on_process_exit",
            attempt=self.attempt,
            result="cleared",
            reason=str(result.get("reason") or reason),
            data={"cleared": cleared},
        )
        self._publish_snapshot()

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]:
        result = self._state.force_finalize_live_tool_calls(reason)
        self._publish_snapshot()
        return result

    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]:
        return self._state.active_tool_calls_watchdog_snapshot()

    def stop(self) -> None:
        self._agent.stop()
        self._output_sink.close()

    def _publish_snapshot(self) -> None:
        if self._snapshot_publisher is not None:
            self._snapshot_publisher(self._state.build_snapshot())
