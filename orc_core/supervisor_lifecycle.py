#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional, Tuple

from .logging import debug_log, log_event
from .notify import send_telegram_message

PROCESS_EXIT_GRACE_SECONDS = 3.0

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
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> str:
    start_time = time.time()
    last_stats_key: Optional[Tuple[int, int, int, int]] = None
    same_count = 0
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
        monitor.maybe_report()
        stats_key = (
            monitor.metrics.total_lines,
            monitor.metrics.command_count,
            monitor.metrics.total_output_chars,
            int(monitor.metrics.tokens_total or 0),
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
        if stats_key == last_stats_key:
            same_count += 1
        else:
            same_count = 0
            last_stats_key = stats_key
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
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "task ttl exceeded", task_ttl=task_ttl)
            debug_log(
                "H6",
                "orc_core/supervisor_lifecycle.py:wait_for_completion:ttl",
                "task ttl exceeded",
                {"task_ttl": task_ttl, "elapsed": time.time() - start_time},
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
        monitor.maybe_report()
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
