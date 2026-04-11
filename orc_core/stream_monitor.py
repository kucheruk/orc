#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional, TextIO

from .atomic_io import write_json_atomic
from .logging import log_event, now_ms
from .timeline import timeline_instant
from .process import kill_process_tree
from .process_groups import resolve_process_group_id, subprocess_group_spawn_kwargs, terminate_process_group
from .state_paths import active_task_path, metrics_path, stats_path
from .monitor_types import MonitorSnapshot
from .stream_monitor_state import StreamMonitorState
from .task_state import init_runtime_payload, load_runtime_payload, runtime_state_path
from .task_source import MarkdownTaskSource

GIT_STATS_TIMEOUT_SECONDS = 10.0
STREAM_READER_LIMIT_BYTES = 32 * 1024 * 1024


class _ProcessProxy:
    def __init__(self) -> None:
        self.pid: Optional[int] = None
        self.returncode: Optional[int] = None

    def poll(self) -> Optional[int]:
        return self.returncode


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
        self._agent_cmd = list(agent_cmd)
        self.proc = _ProcessProxy()
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.started_at = time.time()
        self.last_output_time = time.time()
        self.init_pid: Optional[int] = None
        self.process_group_id: Optional[int] = None
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
        self._agent_output_log_path = str(agent_output_log_path or "").strip() or None
        self._child_env_overrides = {str(key): str(value) for key, value in (child_env_overrides or {}).items()}
        self._snapshot_publisher = snapshot_publisher
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
        task_state_override = str(self._child_env_overrides.get("ORC_TASK_FILE", "")).strip()
        self._task_state_path = Path(task_state_override) if task_state_override else active_task_path(self.workdir)
        runtime_override = str(self._child_env_overrides.get("ORC_TASK_RUNTIME_FILE", "")).strip()
        self._task_runtime_state_path = (
            Path(runtime_override) if runtime_override else runtime_state_path(self._task_state_path)
        )
        stats_override = str(self._child_env_overrides.get("ORC_STATS_FILE", "")).strip()
        self._stats_path = Path(stats_override) if stats_override else stats_path(self.workdir)
        metrics_override = str(self._child_env_overrides.get("ORC_METRICS_FILE", "")).strip()
        self._metrics_path = Path(metrics_override) if metrics_override else metrics_path(self.workdir)
        self._run_id = f"{int(self.started_at)}-{self.task_id}"
        self._stop = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._spawned = threading.Event()
        self._spawn_error: Optional[BaseException] = None
        self._first_output_recorded = False
        self._last_live_status_marker: tuple[str, str, int, bool] | None = None
        self._runner_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._runner_thread.start()
        if not self._spawned.wait(timeout=20.0):
            self._close_agent_output_file()
            raise RuntimeError("Failed to start async monitor process")
        if self._spawn_error is not None:
            self._close_agent_output_file()
            raise self._spawn_error

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

    def _record_event(self, event: Dict[str, object]) -> None:
        self.last_output_time = time.time()
        if not self._first_output_recorded:
            self._first_output_recorded = True
            timeline_instant(
                timeline_id=str(getattr(self, "timeline_id", "") or ""),
                task_id=self.task_id,
                step="first_meaningful_output",
                location="orc_core/stream_monitor.py:StreamJsonMonitor._record_event",
                attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
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
        """Write session_id from stream-json as conversation_id to task file.

        This fires on the very first stream event (within ms of agent start),
        eliminating the dependency on hooks for conversation_id capture.
        """
        try:
            if not self._task_state_path.exists():
                return
            payload = json.loads(self._task_state_path.read_text(encoding="utf-8"))
            existing = str(payload.get("conversation_id") or "").strip()
            if existing:
                return
            payload["conversation_id"] = session_id
            from .atomic_io import write_json_atomic
            write_json_atomic(self._task_state_path, payload, ensure_ascii=False, indent=2)
            log_event(self.log_path, "INFO", "conversation_id captured from stream",
                      session_id=session_id, task_id=self.task_id)
        except Exception as exc:
            log_event(self.log_path, "WARN", "failed to persist conversation_id from stream",
                      error=str(exc), session_id=session_id)

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._spawn_and_monitor())
        finally:
            self._loop.close()

    async def _spawn_and_monitor(self) -> None:
        try:
            child_env = os.environ.copy()
            child_env["ORC_RUN_TOKEN"] = self.run_token
            child_env.update(self._child_env_overrides)
            self._proc = await asyncio.create_subprocess_exec(
                *self._agent_cmd,
                cwd=self.workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=STREAM_READER_LIMIT_BYTES,
                env=child_env,
                **subprocess_group_spawn_kwargs(),
            )
        except Exception as exc:
            self._spawn_error = exc
            self._spawned.set()
            log_event(self.log_path, "ERROR", "failed to spawn async subprocess", error=str(exc))
            raise
        self.proc.pid = self._proc.pid
        self.init_pid = self._proc.pid
        self.process_group_id = resolve_process_group_id(self._proc.pid)
        self._spawned.set()
        if self._proc.stdout is None or self._proc.stderr is None:
            self.proc.returncode = 1
            return
        stdout_task = asyncio.create_task(self._read_stdout(self._proc.stdout))
        stderr_task = asyncio.create_task(self._read_stderr(self._proc.stderr))
        await self._proc.wait()
        self.proc.returncode = self._proc.returncode
        self._finalize_orphaned_tool_calls_on_process_exit(
            reason=f"process_exit_rc_{int(self.proc.returncode or 0)}"
        )
        reader_results = await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        for stream_name, result in zip(("stdout", "stderr"), reader_results):
            if isinstance(result, Exception):
                log_event(
                    self.log_path,
                    "ERROR",
                    "stream reader task failed",
                    stream=stream_name,
                    error=str(result),
                    exception_type=type(result).__name__,
                )

    def _append_agent_output(self, stream_name: str, payload: str) -> None:
        if self._agent_output_file is None:
            return
        self._agent_output_file.write(f"[{stream_name}] {payload}")
        if not payload.endswith("\n"):
            self._agent_output_file.write("\n")
        self._agent_output_file.flush()

    async def _append_agent_output_async(self, stream_name: str, payload: str) -> None:
        await asyncio.to_thread(self._append_agent_output, stream_name, payload)

    async def _read_stdout(self, stream: asyncio.StreamReader) -> None:
        try:
            while not self._stop.is_set():
                line = await stream.readline()
                if not line:
                    return
                decoded = line.decode("utf-8", errors="replace")
                await self._append_agent_output_async("stdout", decoded)
                raw = decoded.strip()
                if not raw:
                    continue
                self.last_output_time = time.time()
                try:
                    event = json.loads(raw)
                except Exception as exc:
                    log_event(self.log_path, "WARN", "stream_json_bad_line", error=str(exc), raw=raw[:500])
                    continue
                if isinstance(event, dict):
                    self._record_event(event)
        except Exception as exc:
            log_event(
                self.log_path,
                "ERROR",
                "fatal error reading stdout stream",
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise

    async def _read_stderr(self, stream: asyncio.StreamReader) -> None:
        try:
            while not self._stop.is_set():
                line = await stream.readline()
                if not line:
                    return
                decoded = line.decode("utf-8", errors="replace")
                await self._append_agent_output_async("stderr", decoded)
                raw = decoded.strip()
                if not raw:
                    continue
                self.last_output_time = time.time()
                self.last_stderr_line = raw[:500]
                self.stderr_count += 1
                log_event(self.log_path, "WARN", "agent_stderr", line=self.last_stderr_line)
        except Exception as exc:
            log_event(
                self.log_path,
                "ERROR",
                "fatal error reading stderr stream",
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            raise

    def _update_git_stats(self) -> None:
        from .git_helpers import git_diff_numstat

        started_ms = now_ms()
        unstaged = git_diff_numstat(self.workdir, timeout=GIT_STATS_TIMEOUT_SECONDS)
        staged = git_diff_numstat(self.workdir, cached=True, timeout=GIT_STATS_TIMEOUT_SECONDS)
        if unstaged is None and staged is None:
            timeline_instant(
                timeline_id=str(getattr(self, "timeline_id", "") or ""),
                task_id=self.task_id,
                step="git_stats_update",
                location="orc_core/stream_monitor.py:StreamJsonMonitor._update_git_stats",
                attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
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
            timeline_id=str(getattr(self, "timeline_id", "") or ""),
            task_id=self.task_id,
            step="git_stats_update",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._update_git_stats",
            attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
            result="updated",
            data={"duration_ms": max(now_ms() - started_ms, 0), "files_changed": files_changed},
        )

    def _write_metrics_snapshot(self) -> None:
        try:
            target_metrics_path = getattr(self, "_metrics_path", None)
            if target_metrics_path is None:
                target_metrics_path = Path(self.workdir) / ".orc" / "orc-metrics.json"
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
            timeline_id=str(getattr(self, "timeline_id", "") or ""),
            task_id=self.task_id,
            step="runtime_state_update",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._update_task_runtime_state",
            attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
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
                timeline_id=str(getattr(self, "timeline_id", "") or ""),
                task_id=self.task_id,
                step="live_status_update",
                location="orc_core/stream_monitor.py:StreamJsonMonitor.maybe_report",
                attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
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
            timeline_id=str(getattr(self, "timeline_id", "") or ""),
            task_id=self.task_id,
            step="monitor_maybe_report",
            location="orc_core/stream_monitor.py:StreamJsonMonitor.maybe_report",
            attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
            result="reported",
            data={"duration_ms": max(now_ms() - started_ms, 0)},
        )

    def get_summary_text(self) -> str:
        return self._state.summary_text()

    def send_keys(self, keys: Iterable[str], label: str = "") -> bool:
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        return False

    def refresh_process_status(self) -> Optional[int]:
        proc = self._proc
        if proc is None:
            return self.proc.returncode
        returncode = proc.returncode
        if returncode is not None:
            self.proc.returncode = returncode
        return self.proc.returncode

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
            self.log_path,
            "WARN",
            "forced_tool_close",
            reason=str(result.get("reason") or reason),
            cleared=cleared,
            pending_preview=pending if isinstance(pending, list) else [],
        )
        timeline_instant(
            timeline_id=str(getattr(self, "timeline_id", "") or ""),
            task_id=self.task_id,
            step="forced_tool_close",
            location="orc_core/stream_monitor.py:StreamJsonMonitor._finalize_orphaned_tool_calls_on_process_exit",
            attempt=max(int(getattr(self, "attempt", 0) or 0), 0),
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
        self._stop.set()
        root_pid = self.init_pid or self.proc.pid
        if isinstance(root_pid, int) and root_pid > 0 and self.proc.returncode is None:
            if not terminate_process_group(self.process_group_id, self.log_path, label="stream-monitor-stop"):
                kill_process_tree(root_pid, self.log_path, label="stream-monitor-stop")
        loop = self._loop
        if loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(lambda: None)
            except RuntimeError:
                pass
        if self._runner_thread.is_alive():
            self._runner_thread.join(timeout=2.0)
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
