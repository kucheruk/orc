#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-JSON monitor: parses agent output, collects metrics, publishes snapshots."""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional, TextIO

from .agent_process import AgentProcess
from .atomic_io import write_json_atomic
from .logging import log_event, now_ms
from .timeline import timeline_instant
from .state_paths import active_task_path, metrics_path, stats_path
from .monitor_types import MonitorSnapshot
from .stream_monitor_state import StreamMonitorState
from ..tasks.task_state import init_runtime_payload, load_runtime_payload, runtime_state_path
from ..tasks.task_source import MarkdownTaskSource

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
        self._agent_output_log_path = str(agent_output_log_path or "").strip() or None
        self._agent_output_file: Optional[TextIO] = None
        if self._agent_output_log_path:
            path = Path(self._agent_output_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._agent_output_file = path.open("a", encoding="utf-8")
            self._agent_output_file.write(f"# stream start task_id={self.task_id}\n")
            self._agent_output_file.flush()
            log_event(self.log_path, "INFO", "agent output stream enabled", task_id=self.task_id, path=str(path))

        self._state = StreamMonitorState(task_id=task_id, started_at=self.started_at, summary_lines=summary_lines)
        self.metrics = self._state.metrics
        self._report_interval = max(report_interval, 1.0)
        self._last_report_time = 0.0
        self._last_git_stats_time = 0.0
        child_env = {str(k): str(v) for k, v in (child_env_overrides or {}).items()}
        task_state_override = child_env.get("ORC_TASK_FILE", "").strip()
        self._task_state_path = Path(task_state_override) if task_state_override else active_task_path(self.workdir)
        runtime_override = child_env.get("ORC_TASK_RUNTIME_FILE", "").strip()
        self._task_runtime_state_path = (
            Path(runtime_override) if runtime_override else runtime_state_path(self._task_state_path)
        )
        stats_override = child_env.get("ORC_STATS_FILE", "").strip()
        self._stats_path = Path(stats_override) if stats_override else stats_path(self.workdir)
        metrics_override = child_env.get("ORC_METRICS_FILE", "").strip()
        self._metrics_path = Path(metrics_override) if metrics_override else metrics_path(self.workdir)
        self._run_id = f"{int(self.started_at)}-{self.task_id}"
        self._first_output_recorded = False
        self._last_live_status_marker: tuple[str, str, int, bool] | None = None

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
        self._append_agent_output("stdout", decoded)
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
        self._append_agent_output("stderr", decoded)
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
            self._persist_conversation_id(self._state.session_id)
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

    def _persist_conversation_id(self, session_id: str) -> None:
        try:
            if not self._task_state_path.exists():
                return
            payload = json.loads(self._task_state_path.read_text(encoding="utf-8"))
            existing = str(payload.get("conversation_id") or "").strip()
            if existing:
                return
            payload["conversation_id"] = session_id
            write_json_atomic(self._task_state_path, payload, ensure_ascii=False, indent=2)
            log_event(self.log_path, "INFO", "conversation_id captured from stream",
                      session_id=session_id, task_id=self.task_id)
        except Exception as exc:
            log_event(self.log_path, "WARN", "failed to persist conversation_id from stream",
                      error=str(exc), session_id=session_id)

    # ── Agent output log ────────────────────────────────────────

    def _append_agent_output(self, stream_name: str, payload: str) -> None:
        if self._agent_output_file is None:
            return
        self._agent_output_file.write(f"[{stream_name}] {payload}")
        if not payload.endswith("\n"):
            self._agent_output_file.write("\n")
        self._agent_output_file.flush()

    # ── Periodic reporting ──────────────────────────────────────

    def _update_git_stats(self) -> None:
        from ..git.git_helpers import git_diff_numstat

        started_ms = now_ms()
        unstaged = git_diff_numstat(self.workdir, timeout=GIT_STATS_TIMEOUT_SECONDS)
        staged = git_diff_numstat(self.workdir, cached=True, timeout=GIT_STATS_TIMEOUT_SECONDS)
        if unstaged is None and staged is None:
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="git_stats_update",
                location="orc_core/stream_monitor.py:StreamJsonMonitor._update_git_stats",
                attempt=self.attempt,
                result="skipped",
                reason="git_stats_unavailable",
                data={"duration_ms": max(now_ms() - started_ms, 0)},
            )
            return

        added = 0
        deleted = 0
        files: set[str] = set()
        for output in (unstaged or "", staged or ""):
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                try:
                    added += int(parts[0])
                except ValueError:
                    pass
                try:
                    deleted += int(parts[1])
                except ValueError:
                    pass
                path = parts[2].strip()
                if path:
                    files.add(path)
        self.metrics.git_added = added
        self.metrics.git_deleted = deleted
        files_changed = len(files)
        if files_changed:
            self.metrics.files_edited = files_changed
        timeline_instant(
            timeline_id=self.timeline_id,
            task_id=self.task_id,
            step="git_stats_update",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._update_git_stats",
            attempt=self.attempt,
            result="updated",
            data={"duration_ms": max(now_ms() - started_ms, 0), "files_changed": files_changed},
        )

    def _write_metrics_snapshot(self) -> None:
        try:
            target_metrics_path = self._metrics_path
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "task_id": self.task_id,
                "tokens_total": self.metrics.tokens_total,
                "lines": self.metrics.total_lines,
                "commands": self.metrics.command_count,
                "files_edited": self.metrics.files_edited,
                "git_added": self.metrics.git_added,
                "git_deleted": self.metrics.git_deleted,
                "tokens_status": self.metrics.tokens_status,
                "tokens_source": self.metrics.tokens_source,
            }
            target_metrics_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(target_metrics_path, payload, ensure_ascii=False, indent=2)
        except Exception as exc:
            log_event(self.log_path, "ERROR", "metrics snapshot write failed", error=str(exc))

    def _refresh_backlog_progress(self) -> None:
        backlog_path = Path(self.workdir) / "BACKLOG.md"
        if self._task_state_path.exists():
            try:
                payload = json.loads(self._task_state_path.read_text(encoding="utf-8"))
                candidate = str(payload.get("backlog_path") or "").strip()
                if candidate:
                    backlog_path = Path(candidate)
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        # Kanban mode uses a _board sentinel instead of BACKLOG.md — skip progress refresh
        if backlog_path.name == "_board" or backlog_path.is_dir():
            return
        if not backlog_path.exists():
            return
        try:
            tasks = MarkdownTaskSource(backlog_path).list_tasks()
        except Exception as exc:
            log_event(self.log_path, "WARN", "backlog progress refresh failed", error=str(exc))
            return
        total = len(tasks)
        done = sum(1 for task in tasks if task.done)
        self._state.set_progress(done, total, self._state._progress_in_progress)

    def _update_eta_forecast(self) -> None:
        try:
            stats = json.loads(self._stats_path.read_text(encoding="utf-8")) if self._stats_path.exists() else {}
        except Exception as exc:
            log_event(self.log_path, "WARN", "eta forecast read failed", error=str(exc))
            self._state.set_eta_seconds(None)
            return
        raw_durations = stats.get("recent_durations") or []
        if not isinstance(raw_durations, list):
            self._state.set_eta_seconds(None)
            return
        durations = [int(value) for value in raw_durations if isinstance(value, (int, float)) and value > 0]
        if not durations:
            self._state.set_eta_seconds(None)
            return
        window = durations[-3:]
        avg_seconds = sum(window) / max(len(window), 1)
        snapshot = self._state.build_snapshot()
        remaining = max(snapshot.progress_remaining, 0)
        self._state.set_eta_seconds(avg_seconds * remaining if remaining > 0 else 0.0)

    def _update_task_runtime_state(self) -> None:
        started_ms = now_ms()
        now = time.time()
        runtime_path = self._task_runtime_state_path
        payload = load_runtime_payload(runtime_path)
        if not payload:
            payload = init_runtime_payload(self.task_id)
        if not isinstance(payload, dict):
            return
        if str(payload.get("task_id") or "").strip() != self.task_id:
            return
        active_seconds = float(payload.get("active_seconds") or 0.0)
        last_heartbeat = float(payload.get("last_heartbeat_at") or now)
        run_id = str(payload.get("run_id") or "")
        if run_id == self._run_id:
            active_seconds += max(now - last_heartbeat, 0.0)
        payload["active_seconds"] = active_seconds
        payload["last_heartbeat_at"] = now
        payload["run_id"] = self._run_id
        try:
            write_json_atomic(runtime_path, payload, ensure_ascii=False, indent=2)
        except Exception as exc:
            log_event(self.log_path, "WARN", "task runtime heartbeat write failed", error=str(exc))
        timeline_instant(
            timeline_id=self.timeline_id,
            task_id=self.task_id,
            step="runtime_state_update",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._update_task_runtime_state",
            attempt=self.attempt,
            result="ok",
            data={"duration_ms": max(now_ms() - started_ms, 0)},
        )

    def maybe_report(self) -> None:
        started_ms = now_ms()
        now = time.time()
        if now - self._last_report_time < self._report_interval:
            return
        self._last_report_time = now
        self._refresh_backlog_progress()
        if now - self._last_git_stats_time >= 10.0:
            self._last_git_stats_time = now
            self._update_git_stats()
        self._update_task_runtime_state()
        self._update_eta_forecast()
        self._write_metrics_snapshot()
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
        self._close_agent_output_file()

    def _close_agent_output_file(self) -> None:
        f = self._agent_output_file
        if f is not None:
            self._agent_output_file = None
            try:
                f.close()
            except OSError:
                pass

    def _publish_snapshot(self) -> None:
        if self._snapshot_publisher is not None:
            self._snapshot_publisher(self._state.build_snapshot())
