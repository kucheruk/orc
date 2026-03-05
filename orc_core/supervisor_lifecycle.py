#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
from pathlib import Path
from typing import Callable, Optional

import psutil

from .logging import debug_log, debug_mode_log, log_event, timeline_instant
from .notify import send_telegram_message
from .process import is_pid_alive
from .task_state import delete_runtime_state_file

PROCESS_EXIT_GRACE_SECONDS = 3.0
DONE_BACKLOG_IDLE_GRACE_SECONDS = 20.0
PID_MISSING_GRACE_SECONDS = 1.0
TOOL_DIGESTION_GRACE_SECONDS = 180.0
TOKENS_STUCK_NOTICE_SECONDS = 15 * 60
TOKENS_STUCK_NOTICE_LABEL = "15m"
DEBUG_SESSION_LOG_PATH = Path("/Users/vetinary/work/orc/.cursor/debug-bbb5e7.log")
DEBUG_SESSION_ID = "bbb5e7"


def _task_done_in_backlog(task_path: Path) -> bool:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    backlog_raw = str(payload.get("backlog_path") or "").strip()
    task_id = str(payload.get("task_id") or "").strip()
    if not backlog_raw or not task_id:
        return False
    try:
        from .task_source import MarkdownTaskSource

        return MarkdownTaskSource(Path(backlog_raw)).is_task_done(task_id)
    except Exception:
        return False


def _monitor_pid_missing(monitor) -> bool:
    refresh_status = getattr(monitor, "refresh_process_status", None)
    if callable(refresh_status):
        try:
            refresh_status()
        except Exception:
            pass
    if monitor.proc.poll() is not None:
        return False
    pid = getattr(monitor.proc, "pid", None) or getattr(monitor, "init_pid", None)
    if not isinstance(pid, int) or pid <= 0:
        return False
    return not is_pid_alive(pid)


def _session_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "id": f"log_{int(time.time() * 1000)}_{hypothesis_id}",
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        DEBUG_SESSION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_SESSION_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def _force_close_active_tools_if_needed(monitor, log_path: Path, task_id: str, reason: str) -> None:
    finalize = getattr(monitor, "force_finalize_live_tool_calls", None)
    if not callable(finalize):
        return
    try:
        result = finalize(reason)
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


def _get_active_children_count(monitor) -> int:
    pid = getattr(monitor.proc, "pid", None) or getattr(monitor, "init_pid", None)
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
def wait_for_completion(
    task_path: Path,
    monitor,
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
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> str:
    start_time = time.time()
    pid_missing_since: Optional[float] = None
    last_heartbeat_time = 0.0
    last_tokens_value: Optional[int] = None
    last_tokens_time = time.time()
    last_stuck_notice_time = 0.0
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
        if escape_requested is not None and escape_requested():
            if confirm_exit is None or confirm_exit():
                log_event(log_path, "WARN", "escape interrupt confirmed", task_id=task_id)
                timeline_instant(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=attempt,
                    result="interrupt",
                    reason="escape_confirmed",
                )
                raise KeyboardInterrupt
            log_event(log_path, "INFO", "escape interrupt cancelled", task_id=task_id)
        if not task_path.exists():
            log_event(log_path, "INFO", "task file removed; completion observed")
            debug_log(
                "H3",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:done",
                "task file removed",
                {"task_path": str(task_path)},
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="completed",
                reason="task_file_removed",
            )
            return "completed"
        if _monitor_pid_missing(monitor):
            if pid_missing_since is None:
                pid_missing_since = time.time()
                log_event(log_path, "WARN", "agent pid missing detected; waiting grace", task_id=task_id)
                time.sleep(max(min(poll, 0.2), 0.05))
                continue
            if (time.time() - pid_missing_since) < PID_MISSING_GRACE_SECONDS:
                time.sleep(max(min(poll, 0.2), 0.05))
                continue
            if _task_done_in_backlog(task_path):
                log_event(log_path, "INFO", "agent pid missing and task marked done; treating as completed", task_id=task_id)
                try:
                    task_path.unlink()
                    delete_runtime_state_file(task_path, log_path, reason="pid_missing_task_done")
                except Exception:
                    pass
                timeline_instant(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=attempt,
                    result="completed",
                    reason="pid_missing_task_done",
                )
                return "completed"
            log_event(log_path, "ERROR", "agent pid missing while task still active", task_id=task_id)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="process_exited",
                reason="pid_missing_task_active",
            )
            return "process_exited"
        else:
            pid_missing_since = None
        now = time.time()
        if _task_done_in_backlog(task_path) and (now - monitor.last_output_time) >= DONE_BACKLOG_IDLE_GRACE_SECONDS:
            log_event(log_path, "INFO", "task marked done and agent idle; treating as completed", task_id=task_id)
            try:
                task_path.unlink()
                delete_runtime_state_file(task_path, log_path, reason="idle_task_done")
            except Exception:
                pass
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="completed",
                reason="backlog_done_idle",
            )
            return "completed"
        if (now - last_heartbeat_time) >= 20.0:
            last_heartbeat_time = now
            _session_debug_log(
                "H3",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:heartbeat",
                "wait loop heartbeat before maybe_report",
                {
                    "task_exists": task_path.exists(),
                    "since_last_output": now - monitor.last_output_time,
                    "lines": monitor.metrics.total_lines,
                    "commands": monitor.metrics.command_count,
                    "tokens_total": int(monitor.metrics.tokens_total or 0),
                    "result_status": getattr(monitor, "result_status", None),
                    "ui_followup_prompt": bool(getattr(monitor, "ui_followup_prompt", False)),
                    "proc_pid": getattr(monitor.proc, "pid", None),
                    "proc_returncode": monitor.proc.poll(),
                },
            )
        maybe_report_started = time.time()
        monitor.maybe_report()
        maybe_report_duration = time.time() - maybe_report_started
        if maybe_report_duration >= 2.0:
            _session_debug_log(
                "H2",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:maybe_report",
                "maybe_report is slow",
                {
                    "duration_seconds": maybe_report_duration,
                    "task_exists": task_path.exists(),
                    "since_last_output": time.time() - monitor.last_output_time,
                    "proc_returncode": monitor.proc.poll(),
                },
            )
        timeline_instant(
            timeline_id=timeline_id,
            task_id=task_id,
            step="wait_for_completion_maybe_report",
            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
            attempt=attempt,
            result="ok",
            data={"duration_ms": int(maybe_report_duration * 1000)},
        )
        tokens_value = monitor.metrics.tokens_total
        if tokens_value is not None:
            if last_tokens_value is None or tokens_value != last_tokens_value:
                last_tokens_value = tokens_value
                last_tokens_time = time.time()
            else:
                since_tokens = time.time() - last_tokens_time
                if since_tokens >= TOKENS_STUCK_NOTICE_SECONDS and (
                    time.time() - last_stuck_notice_time
                ) >= TOKENS_STUCK_NOTICE_SECONDS:
                    last_stuck_notice_time = time.time()
                    stuck_msg = f"{task_id} — agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                    if task_text:
                        stuck_msg = (
                            f"{task_id} — {task_text}\n"
                            f"agent stuck (tokens unchanged {TOKENS_STUCK_NOTICE_LABEL})"
                        )
                    send_telegram_message(stuck_msg, log_path)
        if getattr(monitor, "result_status", None) == "success":
            if not task_path.exists():
                return "completed"

        if monitor.proc.poll() is not None:
            returncode = int(monitor.proc.returncode or 0)
            if returncode == 0 and not task_path.exists():
                timeline_instant(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="wait_for_completion_exit",
                    location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                    attempt=attempt,
                    result="completed",
                    reason="process_exit_task_file_removed",
                )
                return "completed"
            if returncode == 0 and task_path.exists():
                grace_deadline = time.time() + PROCESS_EXIT_GRACE_SECONDS
                while time.time() < grace_deadline:
                    if not task_path.exists():
                        log_event(log_path, "INFO", "task file removed during exit grace window")
                        return "completed"
                    if _task_done_in_backlog(task_path):
                        log_event(log_path, "INFO", "task marked done during exit grace window", task_id=task_id)
                        try:
                            task_path.unlink()
                            delete_runtime_state_file(task_path, log_path, reason="exit_grace_task_done")
                        except Exception:
                            pass
                        timeline_instant(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="wait_for_completion_exit",
                            location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                            attempt=attempt,
                            result="completed",
                            reason="exit_grace_task_done",
                        )
                        return "completed"
                    time.sleep(max(min(poll, 0.2), 0.05))
            log_event(log_path, "ERROR", "agent process exited while task still active", returncode=monitor.proc.returncode)
            _force_close_active_tools_if_needed(
                monitor,
                log_path,
                task_id,
                reason=f"process_exited_while_task_active_rc_{returncode}",
            )
            debug_log(
                "H4",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:exit",
                "agent process exited early",
                {
                    "returncode": monitor.proc.returncode,
                    "task_exists": task_path.exists(),
                    "stderr_count": monitor.stderr_count,
                    "last_stderr_line": monitor.last_stderr_line,
                },
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="process_exited",
                reason="process_exited_while_task_active",
                data={"returncode": returncode},
            )
            return "process_exited"
        if getattr(monitor, "ui_followup_prompt", False):
            log_event(log_path, "WARN", "follow-up input requested by agent", task_id=task_id)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="waiting_for_input",
            )
            return "waiting_for_input"
        now = time.time()
        silence_seconds = now - monitor.last_output_time
        snapshot_fn = getattr(monitor, "active_tool_calls_watchdog_snapshot", None)
        tool_snapshot = snapshot_fn() if callable(snapshot_fn) else {}
        active_tools_count = int(tool_snapshot.get("count") or 0) if isinstance(tool_snapshot, dict) else 0
        is_stalled = False
        stall_reason = ""
        if active_tools_count > 0:
            active_children = _get_active_children_count(monitor)
            if active_children <= 0 and silence_seconds > TOOL_DIGESTION_GRACE_SECONDS:
                is_stalled = True
                stall_reason = f"agent_digestion_timeout_{TOOL_DIGESTION_GRACE_SECONDS}s"
        elif silence_seconds > stall_timeout:
            is_stalled = True
            stall_reason = f"stall_timeout_{stall_timeout}s"
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
                    "proc_returncode": monitor.proc.poll(),
                    "task_exists": task_path.exists(),
                },
            )
            log_event(
                log_path,
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
                    "lines": monitor.metrics.total_lines,
                    "task_exists": task_path.exists(),
                },
            )
            if active_tools_count > 0:
                _force_close_active_tools_if_needed(monitor, log_path, task_id, reason=stall_reason)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="stalled",
                data={
                    "since_last_output_ms": int(silence_seconds * 1000),
                    "reason": stall_reason,
                },
            )
            return "stalled"
        total_elapsed = elapsed_before_start + (time.time() - start_time)
        if total_elapsed > task_ttl:
            log_event(log_path, "ERROR", "task ttl exceeded", task_ttl=task_ttl)
            debug_log(
                "H6",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:ttl",
                "task ttl exceeded",
                {"task_ttl": task_ttl, "elapsed": total_elapsed},
            )
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step="wait_for_completion_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_completion",
                attempt=attempt,
                result="ttl_exceeded",
                data={"ttl_elapsed_ms": int(total_elapsed * 1000), "task_ttl_ms": int(task_ttl * 1000)},
            )
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))
    return "completed"


def wait_for_process_exit(
    monitor,
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
) -> str:
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
            return "process_exited"
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
            return "process_exited"
        if stop_on_followup_prompt and getattr(monitor, "ui_followup_prompt", False):
            log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            timeline_instant(
                timeline_id=timeline_id,
                task_id=task_id,
                step=f"{label}_wait_exit",
                location="orc_core/supervisor_lifecycle.py:wait_for_process_exit",
                attempt=attempt,
                result="waiting_for_input",
            )
            return "waiting_for_input"
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
            return "completed" if monitor.proc.returncode == 0 else "process_exited"
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
            return "stalled"
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
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))


async def async_wait_for_completion(**kwargs) -> str:
    return await asyncio.to_thread(wait_for_completion, **kwargs)


async def async_wait_for_process_exit(**kwargs) -> str:
    return await asyncio.to_thread(wait_for_process_exit, **kwargs)
