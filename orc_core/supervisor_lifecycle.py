#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import time
from pathlib import Path
from typing import Callable, Optional

from .logging import debug_log, log_event
from .notify import send_telegram_message
from .process import is_pid_alive

PROCESS_EXIT_GRACE_SECONDS = 3.0
DONE_BACKLOG_IDLE_GRACE_SECONDS = 20.0
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
    elapsed_before_start: float = 0.0,
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> str:
    start_time = time.time()
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
    while True:
        if escape_requested is not None and escape_requested():
            if confirm_exit is None or confirm_exit():
                log_event(log_path, "WARN", "escape interrupt confirmed", task_id=task_id)
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
            return "completed"
        if _monitor_pid_missing(monitor):
            if _task_done_in_backlog(task_path):
                log_event(log_path, "INFO", "agent pid missing and task marked done; treating as completed", task_id=task_id)
                try:
                    task_path.unlink()
                except Exception:
                    pass
                return "completed"
            log_event(log_path, "ERROR", "agent pid missing while task still active", task_id=task_id)
            return "process_exited"
        now = time.time()
        if _task_done_in_backlog(task_path) and (now - monitor.last_output_time) >= DONE_BACKLOG_IDLE_GRACE_SECONDS:
            log_event(log_path, "INFO", "task marked done and agent idle; treating as completed", task_id=task_id)
            try:
                task_path.unlink()
            except Exception:
                pass
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
        tokens_value = monitor.metrics.tokens_total
        if tokens_value is not None:
            if last_tokens_value is None or tokens_value != last_tokens_value:
                last_tokens_value = tokens_value
                last_tokens_time = time.time()
            else:
                since_tokens = time.time() - last_tokens_time
                if since_tokens >= 300 and (time.time() - last_stuck_notice_time) >= 300:
                    last_stuck_notice_time = time.time()
                    stuck_msg = f"{task_id} — agent stuck (tokens unchanged 5m)"
                    if task_text:
                        stuck_msg = f"{task_id} — {task_text}\nagent stuck (tokens unchanged 5m)"
                    send_telegram_message(stuck_msg, log_path)
        if getattr(monitor, "result_status", None) == "success":
            if not task_path.exists():
                return "completed"

        if monitor.proc.poll() is not None:
            returncode = int(monitor.proc.returncode or 0)
            if returncode == 0 and not task_path.exists():
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
                        except Exception:
                            pass
                        return "completed"
                    time.sleep(max(min(poll, 0.2), 0.05))
            log_event(log_path, "ERROR", "agent process exited while task still active", returncode=monitor.proc.returncode)
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
            return "process_exited"
        if getattr(monitor, "ui_followup_prompt", False):
            log_event(log_path, "WARN", "follow-up input requested by agent", task_id=task_id)
            return "waiting_for_input"
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", stall_seconds=stall_timeout)
            debug_log(
                "H5",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:stall",
                "stall detected",
                {
                    "stall_seconds": stall_timeout,
                    "since_last_output": time.time() - monitor.last_output_time,
                    "lines": monitor.metrics.total_lines,
                    "task_exists": task_path.exists(),
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
    while True:
        if escape_requested is not None and escape_requested():
            if confirm_exit is None or confirm_exit():
                log_event(log_path, "WARN", "escape interrupt confirmed", label=label)
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
            return "process_exited"
        if _monitor_pid_missing(monitor):
            log_event(log_path, "ERROR", "phase agent pid missing while still running", label=label)
            return "process_exited"
        if stop_on_followup_prompt and getattr(monitor, "ui_followup_prompt", False):
            log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            return "waiting_for_input"
        if monitor.proc.poll() is not None:
            log_event(
                log_path,
                "INFO" if monitor.proc.returncode == 0 else "ERROR",
                "phase process exited",
                label=label,
                returncode=monitor.proc.returncode,
            )
            return "completed" if monitor.proc.returncode == 0 else "process_exited"
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", label=label, stall_seconds=stall_timeout)
            return "stalled"
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "phase ttl exceeded", label=label, task_ttl=task_ttl)
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))


async def async_wait_for_completion(**kwargs) -> str:
    return await asyncio.to_thread(wait_for_completion, **kwargs)


async def async_wait_for_process_exit(**kwargs) -> str:
    return await asyncio.to_thread(wait_for_process_exit, **kwargs)
