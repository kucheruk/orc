#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-JSON monitor: parses agent output, collects metrics, publishes snapshots."""

import json
import time
import uuid
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional

from ..process.agent_process import AgentProcess
from ..io.logging import log_event, now_ms
from .agent_output_sink import AgentOutputSink
from .conversation_persister import ConversationIdPersister
from .monitor_metrics_collector import MonitorMetricsCollector
from ..io.timeline import timeline_instant
from ..state.state_paths import active_task_path, metrics_path, stats_path

from .monitor_types import MonitorSnapshot
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
        self.stderr_count = 0
        self.last_stderr_line = ""
        self.last_nudge_time = 0.0
        self.status_only_reports = 0
        self.ui_followup_prompt = False
        self.result_status: Optional[str] = None
        self.result_seen_at: Optional[float] = None
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
        child_env = {str(k): str(v) for k, v in (child_env_overrides or {}).items()}
        task_state_override = child_env.get("ORC_TASK_FILE", "").strip()
        self._task_state_path = Path(task_state_override) if task_state_override else active_task_path(self.workdir)
        runtime_override = child_env.get("ORC_TASK_RUNTIME_FILE", "").strip()
        if runtime_override:
            self._task_runtime_state_path = Path(runtime_override)
        else:
            from ..state.runtime_state import runtime_state_path
            self._task_runtime_state_path = runtime_state_path(self._task_state_path)
        stats_override = child_env.get("ORC_STATS_FILE", "").strip()
        self._stats_path = Path(stats_override) if stats_override else stats_path(self.workdir)
        metrics_override = child_env.get("ORC_METRICS_FILE", "").strip()
        self._metrics_path = Path(metrics_override) if metrics_override else metrics_path(self.workdir)
        self._conversation_persister = ConversationIdPersister(
            task_state_path=self._task_state_path,
            task_id=task_id,
            log_path=log_path,
        )
        self._first_output_recorded = False
        self._last_live_status_marker: tuple[str, str, int, bool] | None = None
        self._collector = collector or MonitorMetricsCollector(
            task_id=task_id, workdir=workdir, log_path=log_path,
            metrics=self.metrics,
            task_state_path=self._task_state_path,
            task_runtime_state_path=self._task_runtime_state_path,
            stats_path=self._stats_path, metrics_path=self._metrics_path,
            timeline_id=self.timeline_id, attempt=self.attempt,
            started_at=self.started_at,
            backlog_task_lister=backlog_task_lister,
            git_diff_fn=git_diff_fn,
        )

        # Spawn agent subprocess — callbacks run on the asyncio reader thread
        self._agent = AgentProcess(
            agent_cmd=agent_cmd,
            workdir=workdir,
            log_path=log_path,
            child_env_overrides=child_env,
            run_token=self.run_token,
            on_stdout_line=self._on_stdout_line,
            on_stderr_line=self._on_stderr_line,
            on_process_exit=lambda rc: self._finalize_orphaned_tool_calls_on_process_exit(
                reason=f"process_exit_rc_{rc}",
            ),
        )
        # Expose process proxy for compatibility
        self.proc = self._agent.proc
        self.init_pid = self._agent.init_pid
        self.process_group_id = self._agent.process_group_id

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

    # ── Stream callbacks (called from AgentProcess reader thread) ─

    def _on_stdout_line(self, decoded: str) -> None:
        self._output_sink.append("stdout", decoded)
        raw = decoded.strip()
        if not raw:
            return
        try:
            event = json.loads(raw)
        except Exception as exc:
            log_event(self.log_path, "WARN", "stream_json_bad_line", error=str(exc), raw=raw[:500])
            return
        if isinstance(event, dict):
            self._record_event(event)

    def _on_stderr_line(self, decoded: str) -> None:
        self._output_sink.append("stderr", decoded)
        raw = decoded.strip()
        if not raw:
            return
        self.last_stderr_line = raw[:500]
        self.stderr_count += 1
        log_event(self.log_path, "WARN", "agent_stderr", line=self.last_stderr_line)

    # ── Event processing ────────────────────────────────────────

    def _record_event(self, event: Dict[str, object]) -> None:
        if not self._first_output_recorded:
            self._first_output_recorded = True
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="first_meaningful_output",
                location="orc_core/stream_monitor.py:StreamJsonMonitor._record_event",
                attempt=self.attempt,
                result="received",
                data={"latency_ms": max(now_ms() - int(self.started_at * 1000), 0)},
            )
        had_session_id = self._state.session_id is not None
        event_type, subtype, raw = self._state.record_event(event)
        if not had_session_id and self._state.session_id is not None:
            self._conversation_persister.persist(self._state.session_id)
        if event_type == "result":
            status = subtype or str(event.get("status") or "")
            self.result_status = status.lower() if status else "success"
            self.result_seen_at = time.time()
        if self._is_followup_prompt_event(event_type, subtype, raw):
            self.ui_followup_prompt = True
        log_event(self.log_path, "INFO", "stream_json_event", event_type=event_type, subtype=subtype, size=len(raw))
        self._publish_snapshot()

    def _is_followup_prompt_event(self, event_type: str, subtype: str, raw: str) -> bool:
        if event_type != "result":
            return False
        status = (subtype or "").strip().lower()
        if status not in {"error", "failed", "failure"}:
            return False
        normalized = raw.lower()
        markers = (
            "add a follow-up",
            "follow-up",
            "follow up",
            "need your input",
            "waiting for your input",
        )
        return any(marker in normalized for marker in markers)

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
