#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
from pathlib import Path
from typing import Callable, Optional

import psutil

from .task_execution_types import TaskCompletionStatus
from .logging import log_event
from .debug_log import debug_log, debug_mode_log
from .monitor_protocol import StreamMonitorProtocol
from .timeline import timeline_instant
from .notify import send_telegram_message
from .process import is_pid_alive
from .task_state import delete_runtime_state_file

PROCESS_EXIT_GRACE_SECONDS = 3.0
DONE_BACKLOG_IDLE_GRACE_SECONDS = 20.0
PID_MISSING_GRACE_SECONDS = 1.0
TOOL_DIGESTION_GRACE_SECONDS = 180.0
TOKENS_STUCK_NOTICE_SECONDS = 15 * 60
TOKENS_STUCK_NOTICE_LABEL = "15m"


def _task_done_in_backlog(task_path: Path) -> bool:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    backlog_raw = str(payload.get("backlog_path") or "").strip()
    task_id = str(payload.get("task_id") or "").strip()
    if not backlog_raw or not task_id:
        return False
    try:
        from .task_source import MarkdownTaskSource

        return MarkdownTaskSource(Path(backlog_raw)).is_task_done(task_id)
    except (OSError, json.JSONDecodeError, ValueError, KeyError):
        return False


def _monitor_pid_missing(monitor: StreamMonitorProtocol) -> bool:
    try:
        monitor.refresh_process_status()
    except Exception:
        pass
    if monitor.proc.poll() is not None:
        return False
    pid = monitor.proc.pid or monitor.init_pid
    if not isinstance(pid, int) or pid <= 0:
        return False
    return not is_pid_alive(pid)


def _is_model_unavailable_stderr(last_stderr_line: str) -> bool:
    normalized = str(last_stderr_line or "").strip().lower()
    if not normalized:
        return False
    markers = (
        "cannot use this model",
        "unknown model",
        "model not found",
        "invalid model",
    )
    return any(marker in normalized for marker in markers)




def _force_close_active_tools_if_needed(monitor: StreamMonitorProtocol, log_path: Path, task_id: str, reason: str) -> None:
    try:
        result = monitor.force_finalize_live_tool_calls(reason)
    except Exception as exc:
        log_event(log_path, "WARN", "force close tools failed", task_id=task_id, reason=reason, error=str(exc))
        return
    cleared = int(result.get("cleared") or 0)
    if cleared <= 0:
        return
    pending = result.get("pending")
    log_event(
        log_path,
        "WARN",
        "force closed active tools",
        task_id=task_id,
        reason=str(result.get("reason") or reason),
        cleared=cleared,
        pending_preview=pending if isinstance(pending, list) else [],
    )


def _get_active_children_count(monitor: StreamMonitorProtocol) -> int:
    pid = monitor.proc.pid or monitor.init_pid
    if not isinstance(pid, int) or pid <= 0:
        return 0
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return 0
    active_count = 0
    for child in children:
        try:
            if child.status() != psutil.STATUS_ZOMBIE:
                active_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            continue
    return active_count
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

        self.start_time = time.time()
        self.pid_missing_since: Optional[float] = None
        self.last_heartbeat_time = 0.0
        self.last_tokens_value: Optional[int] = None
        self.last_tokens_time = time.time()
        self.last_stuck_notice_time = 0.0
        self.backlog_done_at_start = _task_done_in_backlog(task_path)

    def _check_escape(self) -> Optional[TaskCompletionStatus]:
        if self.escape_requested is not None and self.escape_requested():
            if self.confirm_exit is None or self.confirm_exit():
                log_event(self.log_path, "WARN", "escape interrupt confirmed", task_id=self.task_id)
                timeline_instant(
                    timeline_id=self.timeline_id,
                    task_id=self.task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=self.attempt,
                    result="interrupt",
                    reason="escape_confirmed",
                )
                raise KeyboardInterrupt
            log_event(self.log_path, "INFO", "escape interrupt cancelled", task_id=self.task_id)
        return None

    def _check_task_file_removed(self) -> Optional[TaskCompletionStatus]:
        if not self.task_path.exists():
            log_event(self.log_path, "INFO", "task file removed; completion observed")
            debug_log(
                "H3",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:done",
                "task file removed",
                {"task_path": str(self.task_path)},
            )
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="completed",
                reason="task_file_removed",
            )
            return TaskCompletionStatus.COMPLETED
        return None

    def _check_pid_missing(self) -> Optional[TaskCompletionStatus]:
        if _monitor_pid_missing(self.monitor):
            if self.pid_missing_since is None:
                self.pid_missing_since = time.time()
                log_event(self.log_path, "WARN", "agent pid missing detected; waiting grace", task_id=self.task_id)
                time.sleep(max(min(self.poll, 0.2), 0.05))
                return None  # continue to next iteration
            if (time.time() - self.pid_missing_since) < PID_MISSING_GRACE_SECONDS:
                time.sleep(max(min(self.poll, 0.2), 0.05))
                return None  # continue to next iteration
            backlog_done = _task_done_in_backlog(self.task_path)
            if backlog_done and not (self.ignore_initial_backlog_done and self.backlog_done_at_start):
                log_event(self.log_path, "INFO", "agent pid missing and task marked done; treating as completed", task_id=self.task_id)
                try:
                    self.task_path.unlink()
                    delete_runtime_state_file(self.task_path, self.log_path, reason="pid_missing_task_done")
                except OSError:
                    pass
                timeline_instant(
                    timeline_id=self.timeline_id,
                    task_id=self.task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=self.attempt,
                    result="completed",
                    reason="pid_missing_task_done",
                )
                return TaskCompletionStatus.COMPLETED
            log_event(self.log_path, "ERROR", "agent pid missing while task still active", task_id=self.task_id)
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="process_exited",
                reason="pid_missing_task_active",
            )
            return TaskCompletionStatus.PROCESS_EXITED
        else:
            self.pid_missing_since = None
        return None

    def _check_backlog_done_idle(self) -> Optional[TaskCompletionStatus]:
        now = time.time()
        backlog_done = _task_done_in_backlog(self.task_path)
        if (
            backlog_done
            and not (self.ignore_initial_backlog_done and self.backlog_done_at_start)
            and (now - self.monitor.last_output_time) >= DONE_BACKLOG_IDLE_GRACE_SECONDS
        ):
            log_event(self.log_path, "INFO", "task marked done and agent idle; treating as completed", task_id=self.task_id)
            try:
                self.task_path.unlink()
                delete_runtime_state_file(self.task_path, self.log_path, reason="idle_task_done")
            except OSError:
                pass
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="completed",
                reason="backlog_done_idle",
            )
            return TaskCompletionStatus.COMPLETED
        return None

    def _check_tokens_stuck(self) -> None:
        tokens_value = self.monitor.metrics.tokens_total
        if tokens_value is not None:
            if self.last_tokens_value is None or tokens_value != self.last_tokens_value:
                self.last_tokens_value = tokens_value
                self.last_tokens_time = time.time()
            else:
                since_tokens = time.time() - self.last_tokens_time
                if since_tokens >= TOKENS_STUCK_NOTICE_SECONDS and (
                    time.time() - self.last_stuck_notice_time
                ) >= TOKENS_STUCK_NOTICE_SECONDS:
                    self.last_stuck_notice_time = time.time()
                    stuck_msg = f"{self.task_id} — agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                    if self.task_text:
                        stuck_msg = (
                            f"{self.task_id} — {self.task_text}\n"
                            f"agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                        )
                    send_telegram_message(stuck_msg, self.log_path)

    def _check_process_exited(self) -> Optional[TaskCompletionStatus]:
        if self.monitor.result_status == "success":
            if not self.task_path.exists():
                return TaskCompletionStatus.COMPLETED

        if self.monitor.proc.poll() is not None:
            returncode = int(self.monitor.proc.returncode or 0)
            if returncode == 0 and not self.task_path.exists():
                timeline_instant(
                    timeline_id=self.timeline_id,
                    task_id=self.task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=self.attempt,
                    result="completed",
                    reason="process_exit_task_file_removed",
                )
                return TaskCompletionStatus.COMPLETED
            if returncode == 0 and self.task_path.exists():
                # Check stream result_status first (hook-free completion detection)
                stream_result = self.monitor.result_status
                if stream_result == "success":
                    log_event(self.log_path, "INFO", "completed via stream result_status=success",
                              task_id=self.task_id)
                    timeline_instant(
                        timeline_id=self.timeline_id,
                        task_id=self.task_id,
                        step="wait_for_completion_exit",
                        location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                        attempt=self.attempt,
                        result="completed",
                        reason="stream_result_success",
                    )
                    return TaskCompletionStatus.COMPLETED
                grace_deadline = time.time() + PROCESS_EXIT_GRACE_SECONDS
                while time.time() < grace_deadline:
                    if not self.task_path.exists():
                        log_event(self.log_path, "INFO", "task file removed during exit grace window")
                        return TaskCompletionStatus.COMPLETED
                    if _task_done_in_backlog(self.task_path):
                        log_event(self.log_path, "INFO", "task marked done during exit grace window", task_id=self.task_id)
                        try:
                            self.task_path.unlink()
                            delete_runtime_state_file(self.task_path, self.log_path, reason="exit_grace_task_done")
                        except OSError:
                            pass
                        timeline_instant(
                            timeline_id=self.timeline_id,
                            task_id=self.task_id,
                            step="wait_for_completion_exit",
                            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                            attempt=self.attempt,
                            result="completed",
                            reason="exit_grace_task_done",
                        )
                        return TaskCompletionStatus.COMPLETED
                    time.sleep(max(min(self.poll, 0.2), 0.05))
            if _is_model_unavailable_stderr(self.monitor.last_stderr_line):
                log_event(
                    self.log_path,
                    "ERROR",
                    "agent model unavailable",
                    returncode=self.monitor.proc.returncode,
                    stderr_line=self.monitor.last_stderr_line,
                )
                timeline_instant(
                    timeline_id=self.timeline_id,
                    task_id=self.task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=self.attempt,
                    result="model_unavailable",
                    reason="agent_model_unavailable",
                    data={"returncode": returncode},
                )
                return TaskCompletionStatus.MODEL_UNAVAILABLE
            log_event(self.log_path, "ERROR", "agent process exited while task still active", returncode=self.monitor.proc.returncode)
            _force_close_active_tools_if_needed(
                self.monitor,
                self.log_path,
                self.task_id,
                reason=f"process_exited_while_task_active_rc_{returncode}",
            )
            debug_log(
                "H4",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:exit",
                "agent process exited early",
                {
                    "returncode": self.monitor.proc.returncode,
                    "task_exists": self.task_path.exists(),
                    "stderr_count": self.monitor.stderr_count,
                    "last_stderr_line": self.monitor.last_stderr_line,
                },
            )
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="process_exited",
                reason="process_exited_while_task_active",
                data={"returncode": returncode},
            )
            return TaskCompletionStatus.PROCESS_EXITED
        return None

    def _check_followup_prompt(self) -> Optional[TaskCompletionStatus]:
        if self.monitor.ui_followup_prompt:
            log_event(self.log_path, "WARN", "follow-up input requested by agent", task_id=self.task_id)
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="waiting_for_input",
            )
            return TaskCompletionStatus.WAITING_FOR_INPUT
        return None

    def _check_stall(self) -> Optional[TaskCompletionStatus]:
        now = time.time()
        silence_seconds = now - self.monitor.last_output_time
        tool_snapshot = self.monitor.active_tool_calls_watchdog_snapshot()
        active_tools_count = int(tool_snapshot.get("count") or 0) if isinstance(tool_snapshot, dict) else 0
        is_stalled = False
        stall_reason = ""
        if active_tools_count > 0:
            active_children = _get_active_children_count(self.monitor)
            if active_children <= 0 and silence_seconds > TOOL_DIGESTION_GRACE_SECONDS:
                is_stalled = True
                stall_reason = f"agent_digestion_timeout_{TOOL_DIGESTION_GRACE_SECONDS}s"
        elif silence_seconds > self.stall_timeout:
            is_stalled = True
            stall_reason = f"stall_timeout_{self.stall_timeout}s"
        if is_stalled:
            debug_mode_log(
                "run1",
                "H5",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:stall_timeout",
                "stall timeout reached",
                {
                    "silence_seconds": float(silence_seconds),
                    "reason": stall_reason,
                    "active_tools": active_tools_count,
                    "tool_snapshot": tool_snapshot if isinstance(tool_snapshot, dict) else {},
                    "proc_returncode": self.monitor.proc.poll(),
                    "task_exists": self.task_path.exists(),
                },
            )
            log_event(
                self.log_path,
                "ERROR",
                "stall detected",
                stall_seconds=silence_seconds,
                reason=stall_reason,
                active_tools=active_tools_count,
            )
            debug_log(
                "H5",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:stall",
                "stall detected",
                {
                    "stall_seconds": silence_seconds,
                    "reason": stall_reason,
                    "active_tools": active_tools_count,
                    "lines": self.monitor.metrics.total_lines,
                    "task_exists": self.task_path.exists(),
                },
            )
            if active_tools_count > 0:
                _force_close_active_tools_if_needed(self.monitor, self.log_path, self.task_id, reason=stall_reason)
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="stalled",
                data={
                    "since_last_output_ms": int(silence_seconds * 1000),
                    "reason": stall_reason,
                },
            )
            return TaskCompletionStatus.STALLED
        return None

    def _check_ttl(self) -> Optional[TaskCompletionStatus]:
        total_elapsed = self.elapsed_before_start + (time.time() - self.start_time)
        if total_elapsed > self.task_ttl:
            log_event(self.log_path, "ERROR", "task ttl exceeded", task_ttl=self.task_ttl)
            debug_log(
                "H6",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:ttl",
                "task ttl exceeded",
                {"task_ttl": self.task_ttl, "elapsed": total_elapsed},
            )
            timeline_instant(
                timeline_id=self.timeline_id,
                task_id=self.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=self.attempt,
                result="ttl_exceeded",
                data={"ttl_elapsed_ms": int(total_elapsed * 1000), "task_ttl_ms": int(self.task_ttl * 1000)},
            )
            return TaskCompletionStatus.TTL_EXCEEDED
        return None

    def _maybe_report(self) -> None:
        maybe_report_started = time.time()
        self.monitor.maybe_report()
        maybe_report_duration = time.time() - maybe_report_started
        timeline_instant(
            timeline_id=self.timeline_id,
            task_id=self.task_id,
            step="wait_for_completion_maybe_report",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=self.attempt,
            result="ok",
            data={"duration_ms": int(maybe_report_duration * 1000)},
        )

    def check(self) -> Optional[TaskCompletionStatus]:
        """Run one iteration of checks. Returns a status if done, or None to continue."""
        result = self._check_escape()
        if result is not None:
            return result

        result = self._check_task_file_removed()
        if result is not None:
            return result

        result = self._check_pid_missing()
        if result is not None:
            return result

        result = self._check_backlog_done_idle()
        if result is not None:
            return result

        self._maybe_report()

        self._check_tokens_stuck()

        result = self._check_process_exited()
        if result is not None:
            return result

        result = self._check_followup_prompt()
        if result is not None:
            return result

        result = self._check_stall()
        if result is not None:
            return result

        result = self._check_ttl()
        if result is not None:
            return result

        return None


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
        result = cm.check()
        if result is not None:
            return result
        time.sleep(max(poll, 0.2))


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
    start_time = time.time()
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
        timeline_id=timeline_id,
        task_id=task_id,
        step=f"{label}_wait_loop",
        location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
        attempt=attempt,
        result="start",
        data={"poll_ms": int(max(poll, 0.2) * 1000), "stall_timeout_ms": int(stall_timeout * 1000)},
    )
    while True:
        if escape_requested is not None and escape_requested():
            if confirm_exit is None or confirm_exit():
                log_event(log_path, "WARN", "escape interrupt confirmed", label=label)
                timeline_instant(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step=f"{label}_wait_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                    attempt=attempt,
                    result="interrupt",
                    reason="escape_confirmed",
                )
                raise KeyboardInterrupt
            log_event(log_path, "INFO", "escape interrupt cancelled", label=label)
        try:
            monitor.maybe_report()
        except Exception as exc:
            log_event(
                log_path,
                "ERROR",
                "phase monitor maybe_report crashed",
                label=label,
                error=str(exc),
                exception_type=type(exc).__name__,
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="process_exited",
                reason="maybe_report_exception",
            )
            return TaskCompletionStatus.PROCESS_EXITED
        if _monitor_pid_missing(monitor):
            log_event(log_path, "ERROR", "phase agent pid missing while still running", label=label)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="process_exited",
                reason="pid_missing",
            )
            return TaskCompletionStatus.PROCESS_EXITED
        if stop_on_followup_prompt and monitor.ui_followup_prompt:
            log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="waiting_for_input",
            )
            return TaskCompletionStatus.WAITING_FOR_INPUT
        if monitor.proc.poll() is not None:
            log_event(
                log_path,
                "INFO" if monitor.proc.returncode == 0 else "ERROR",
                "phase process exited",
                label=label,
                returncode=monitor.proc.returncode,
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="completed" if monitor.proc.returncode == 0 else "process_exited",
                data={"returncode": int(monitor.proc.returncode or 0)},
            )
            return TaskCompletionStatus.COMPLETED if monitor.proc.returncode == 0 else TaskCompletionStatus.PROCESS_EXITED
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", label=label, stall_seconds=stall_timeout)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="stalled",
                data={
                    "since_last_output_ms": int((time.time() - monitor.last_output_time) * 1000),
                    "stall_timeout_ms": int(stall_timeout * 1000),
                },
            )
            return TaskCompletionStatus.STALLED
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "phase ttl exceeded", label=label, task_ttl=task_ttl)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="ttl_exceeded",
                data={"task_ttl_ms": int(task_ttl * 1000)},
            )
            return TaskCompletionStatus.TTL_EXCEEDED
        time.sleep(max(poll, 0.2))


async def async_wait_for_completion(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_completion, **kwargs)


async def async_wait_for_process_exit(**kwargs) -> TaskCompletionStatus:
    return await asyncio.to_thread(wait_for_process_exit, **kwargs)
