#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completion check handlers — Chain of Responsibility pattern.

Each check function implements the CompletionCheck protocol:
takes a CompletionMonitor instance and returns Optional[TaskCompletionStatus].
None means "continue to next check", a status means "done".

Register new checks in DEFAULT_CHECK_CHAIN to extend without modifying
the CompletionMonitor.check() method (OCP).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Optional

import psutil

from ..tasks.task_status_types import TaskCompletionStatus
from ..log import log_event
from ..infra.io.debug_log import debug_log, debug_mode_log
from ..infra.io.timeline import timeline_instant
from ..infra.process.process import is_pid_alive
from ..tasks.task_state import delete_runtime_state_file

if TYPE_CHECKING:
    from .lifecycle import CompletionMonitor
    from ..infra.monitoring.monitor_protocol import StreamMonitorProtocol

# Protocol for completion checks: (CompletionMonitor) -> Optional[TaskCompletionStatus]
CompletionCheck = Callable[["CompletionMonitor"], Optional[TaskCompletionStatus]]

PROCESS_EXIT_GRACE_SECONDS = 3.0
DONE_BACKLOG_IDLE_GRACE_SECONDS = 20.0
PID_MISSING_GRACE_SECONDS = 1.0
TOOL_DIGESTION_GRACE_SECONDS = 180.0
TOKENS_STUCK_NOTICE_SECONDS = 15 * 60
TOKENS_STUCK_NOTICE_LABEL = "15m"


# ── Helpers ──────────────────────────────────────────────────────

def _task_done_in_backlog(task_path) -> bool:
    import json
    from pathlib import Path
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    backlog_raw = str(payload.get("backlog_path") or "").strip()
    task_id = str(payload.get("task_id") or "").strip()
    if not backlog_raw or not task_id:
        return False
    try:
        from ..tasks.task_source import MarkdownTaskSource
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


def _force_close_active_tools_if_needed(monitor: StreamMonitorProtocol, log_path, task_id: str, reason: str) -> None:
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


# ── Check functions ──────────────────────────────────────────────

def check_escape(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    if cm.escape_requested is not None and cm.escape_requested():
        if cm.confirm_exit is None or cm.confirm_exit():
            log_event(cm.log_path, "WARN", "escape interrupt confirmed", task_id=cm.task_id)
            timeline_instant(
                timeline_id=cm.timeline_id, task_id=cm.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=cm.attempt, result="interrupt", reason="escape_confirmed",
            )
            raise KeyboardInterrupt
        log_event(cm.log_path, "INFO", "escape interrupt cancelled", task_id=cm.task_id)
    return None


def check_task_file_removed(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    if not cm.task_path.exists():
        log_event(cm.log_path, "INFO", "task file removed; completion observed")
        debug_log(
            "H3", "orc_core/supervisor_lifecycle.py:wait_for_completion:done",
            "task file removed", {"task_path": str(cm.task_path)},
        )
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="completed", reason="task_file_removed",
        )
        return TaskCompletionStatus.COMPLETED
    return None


def check_pid_missing(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    if _monitor_pid_missing(cm.monitor):
        if cm.pid_missing_since is None:
            cm.pid_missing_since = time.time()
            log_event(cm.log_path, "WARN", "agent pid missing detected; waiting grace", task_id=cm.task_id)
            time.sleep(max(min(cm.poll, 0.2), 0.05))
            return None
        if (time.time() - cm.pid_missing_since) < PID_MISSING_GRACE_SECONDS:
            time.sleep(max(min(cm.poll, 0.2), 0.05))
            return None
        backlog_done = _task_done_in_backlog(cm.task_path)
        if backlog_done and not (cm.ignore_initial_backlog_done and cm.backlog_done_at_start):
            log_event(cm.log_path, "INFO", "agent pid missing and task marked done; treating as completed", task_id=cm.task_id)
            try:
                cm.task_path.unlink()
                delete_runtime_state_file(cm.task_path, cm.log_path, reason="pid_missing_task_done")
            except OSError:
                pass
            timeline_instant(
                timeline_id=cm.timeline_id, task_id=cm.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=cm.attempt, result="completed", reason="pid_missing_task_done",
            )
            return TaskCompletionStatus.COMPLETED
        log_event(cm.log_path, "ERROR", "agent pid missing while task still active", task_id=cm.task_id)
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="process_exited", reason="pid_missing_task_active",
        )
        return TaskCompletionStatus.PROCESS_EXITED
    else:
        cm.pid_missing_since = None
    return None


def check_backlog_done_idle(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    now = time.time()
    backlog_done = _task_done_in_backlog(cm.task_path)
    if (
        backlog_done
        and not (cm.ignore_initial_backlog_done and cm.backlog_done_at_start)
        and (now - cm.monitor.last_output_time) >= DONE_BACKLOG_IDLE_GRACE_SECONDS
    ):
        log_event(cm.log_path, "INFO", "task marked done and agent idle; treating as completed", task_id=cm.task_id)
        try:
            cm.task_path.unlink()
            delete_runtime_state_file(cm.task_path, cm.log_path, reason="idle_task_done")
        except OSError:
            pass
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="completed", reason="backlog_done_idle",
        )
        return TaskCompletionStatus.COMPLETED
    return None


def check_tokens_stuck(cm: CompletionMonitor) -> None:
    tokens_value = cm.monitor.metrics.tokens_total
    if tokens_value is not None:
        if cm.last_tokens_value is None or tokens_value != cm.last_tokens_value:
            cm.last_tokens_value = tokens_value
            cm.last_tokens_time = time.time()
        else:
            since_tokens = time.time() - cm.last_tokens_time
            if since_tokens >= TOKENS_STUCK_NOTICE_SECONDS and (
                time.time() - cm.last_stuck_notice_time
            ) >= TOKENS_STUCK_NOTICE_SECONDS:
                cm.last_stuck_notice_time = time.time()
                stuck_msg = f"{cm.task_id} — agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                if cm.task_text:
                    stuck_msg = (
                        f"{cm.task_id} — {cm.task_text}\n"
                        f"agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                    )
                if cm.on_notify:
                    cm.on_notify(stuck_msg)


def check_process_exited(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    if cm.monitor.result_status == "success":
        if not cm.task_path.exists():
            return TaskCompletionStatus.COMPLETED

    if cm.monitor.proc.poll() is not None:
        returncode = int(cm.monitor.proc.returncode or 0)
        if returncode == 0 and not cm.task_path.exists():
            timeline_instant(
                timeline_id=cm.timeline_id, task_id=cm.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=cm.attempt, result="completed", reason="process_exit_task_file_removed",
            )
            return TaskCompletionStatus.COMPLETED
        if returncode == 0 and cm.task_path.exists():
            stream_result = cm.monitor.result_status
            if stream_result == "success":
                log_event(cm.log_path, "INFO", "completed via stream result_status=success", task_id=cm.task_id)
                timeline_instant(
                    timeline_id=cm.timeline_id, task_id=cm.task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=cm.attempt, result="completed", reason="stream_result_success",
                )
                return TaskCompletionStatus.COMPLETED
            grace_deadline = time.time() + PROCESS_EXIT_GRACE_SECONDS
            while time.time() < grace_deadline:
                if not cm.task_path.exists():
                    log_event(cm.log_path, "INFO", "task file removed during exit grace window")
                    return TaskCompletionStatus.COMPLETED
                if _task_done_in_backlog(cm.task_path):
                    log_event(cm.log_path, "INFO", "task marked done during exit grace window", task_id=cm.task_id)
                    try:
                        cm.task_path.unlink()
                        delete_runtime_state_file(cm.task_path, cm.log_path, reason="exit_grace_task_done")
                    except OSError:
                        pass
                    timeline_instant(
                        timeline_id=cm.timeline_id, task_id=cm.task_id,
                        step="wait_for_completion_exit",
                        location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                        attempt=cm.attempt, result="completed", reason="exit_grace_task_done",
                    )
                    return TaskCompletionStatus.COMPLETED
                time.sleep(max(min(cm.poll, 0.2), 0.05))
        if _is_model_unavailable_stderr(cm.monitor.last_stderr_line):
            log_event(
                cm.log_path, "ERROR", "agent model unavailable",
                returncode=cm.monitor.proc.returncode, stderr_line=cm.monitor.last_stderr_line,
            )
            timeline_instant(
                timeline_id=cm.timeline_id, task_id=cm.task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=cm.attempt, result="model_unavailable", reason="agent_model_unavailable",
                data={"returncode": returncode},
            )
            return TaskCompletionStatus.MODEL_UNAVAILABLE
        log_event(cm.log_path, "ERROR", "agent process exited while task still active", returncode=cm.monitor.proc.returncode)
        _force_close_active_tools_if_needed(
            cm.monitor, cm.log_path, cm.task_id,
            reason=f"process_exited_while_task_active_rc_{returncode}",
        )
        debug_log(
            "H4", "orc_core/supervisor_lifecycle.py:wait_for_completion:exit",
            "agent process exited early",
            {
                "returncode": cm.monitor.proc.returncode,
                "task_exists": cm.task_path.exists(),
                "stderr_count": cm.monitor.stderr_count,
                "last_stderr_line": cm.monitor.last_stderr_line,
            },
        )
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="process_exited", reason="process_exited_while_task_active",
            data={"returncode": returncode},
        )
        return TaskCompletionStatus.PROCESS_EXITED
    return None


def check_followup_prompt(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    if cm.monitor.ui_followup_prompt:
        log_event(cm.log_path, "WARN", "follow-up input requested by agent", task_id=cm.task_id)
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="waiting_for_input",
        )
        return TaskCompletionStatus.WAITING_FOR_INPUT
    return None


def check_stall(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    now = time.time()
    silence_seconds = now - cm.monitor.last_output_time
    tool_snapshot = cm.monitor.active_tool_calls_watchdog_snapshot()
    active_tools_count = int(tool_snapshot.get("count") or 0) if isinstance(tool_snapshot, dict) else 0
    is_stalled = False
    stall_reason = ""
    if active_tools_count > 0:
        active_children = _get_active_children_count(cm.monitor)
        if active_children <= 0 and silence_seconds > TOOL_DIGESTION_GRACE_SECONDS:
            is_stalled = True
            stall_reason = f"agent_digestion_timeout_{TOOL_DIGESTION_GRACE_SECONDS}s"
    elif silence_seconds > cm.stall_timeout:
        is_stalled = True
        stall_reason = f"stall_timeout_{cm.stall_timeout}s"
    if is_stalled:
        debug_mode_log(
            "run1", "H5",
            "orc_core/supervisor_lifecycle.py:wait_for_completion:stall_timeout",
            "stall timeout reached",
            {
                "silence_seconds": float(silence_seconds),
                "reason": stall_reason,
                "active_tools": active_tools_count,
                "tool_snapshot": tool_snapshot if isinstance(tool_snapshot, dict) else {},
                "proc_returncode": cm.monitor.proc.poll(),
                "task_exists": cm.task_path.exists(),
            },
        )
        log_event(
            cm.log_path, "ERROR", "stall detected",
            stall_seconds=silence_seconds, reason=stall_reason, active_tools=active_tools_count,
        )
        debug_log(
            "H5", "orc_core/supervisor_lifecycle.py:wait_for_completion:stall",
            "stall detected",
            {
                "stall_seconds": silence_seconds,
                "reason": stall_reason,
                "active_tools": active_tools_count,
                "lines": cm.monitor.metrics.total_lines,
                "task_exists": cm.task_path.exists(),
            },
        )
        if active_tools_count > 0:
            _force_close_active_tools_if_needed(cm.monitor, cm.log_path, cm.task_id, reason=stall_reason)
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="stalled",
            data={"since_last_output_ms": int(silence_seconds * 1000), "reason": stall_reason},
        )
        return TaskCompletionStatus.STALLED
    return None


def check_ttl(cm: CompletionMonitor) -> Optional[TaskCompletionStatus]:
    total_elapsed = cm.elapsed_before_start + (time.time() - cm.start_time)
    if total_elapsed > cm.task_ttl:
        log_event(cm.log_path, "ERROR", "task ttl exceeded", task_ttl=cm.task_ttl)
        debug_log(
            "H6", "orc_core/supervisor_lifecycle.py:wait_for_completion:ttl",
            "task ttl exceeded", {"task_ttl": cm.task_ttl, "elapsed": total_elapsed},
        )
        timeline_instant(
            timeline_id=cm.timeline_id, task_id=cm.task_id,
            step="wait_for_completion_exit",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=cm.attempt, result="ttl_exceeded",
            data={"ttl_elapsed_ms": int(total_elapsed * 1000), "task_ttl_ms": int(cm.task_ttl * 1000)},
        )
        return TaskCompletionStatus.TTL_EXCEEDED
    return None


def maybe_report(cm: CompletionMonitor) -> None:
    cm.monitor.maybe_report()
    timeline_instant(
        timeline_id=cm.timeline_id, task_id=cm.task_id,
        step="wait_for_completion_maybe_report",
        location="orc_core/supervisor_lifecycle.py:wait_for_completion",
        attempt=cm.attempt, result="ok",
    )


# ── Default check chain (OCP: add/remove/reorder here) ────────

DEFAULT_CHECK_CHAIN: tuple[CompletionCheck, ...] = (
    check_escape,
    check_task_file_removed,
    check_pid_missing,
    check_backlog_done_idle,
    maybe_report,           # side-effect only (returns None)
    check_tokens_stuck,     # side-effect only (returns None)
    check_process_exited,
    check_followup_prompt,
    check_stall,
    check_ttl,
)
