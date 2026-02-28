#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from pathlib import Path
from typing import Optional, Tuple

from .backlog import is_task_done
from .logging import debug_log, log_event
from .notify import send_telegram_message
from .supervisor_fallback import hard_cleanup_after_success, invoke_stop_hook_fallback, load_task_payload


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
) -> str:
    start_time = time.time()
    last_stats_key: Optional[Tuple[int, int, int, int]] = None
    same_count = 0
    last_tokens_value: Optional[int] = None
    last_tokens_time = time.time()
    last_stuck_notice_time = 0.0
    followup_seen_at: Optional[float] = None
    fallback_invoked = False
    fallback_last_attempt = 0.0
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
        if monitor.ui_followup_prompt:
            if followup_seen_at is None:
                followup_seen_at = time.time()
            if not fallback_invoked and (time.time() - followup_seen_at) >= 20.0:
                try:
                    payload = json.loads(task_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    log_event(log_path, "ERROR", "fallback stop: failed to parse task json", error=str(exc))
                    payload = {}
                backlog_path = payload.get("backlog_path")
                current_task_id = payload.get("task_id")
                if backlog_path and current_task_id and is_task_done(Path(backlog_path), str(current_task_id)):
                    log_event(
                        log_path,
                        "WARN",
                        "follow-up prompt stuck with done task; invoking fallback stop",
                        task_id=current_task_id,
                    )
                    fallback_invoked = invoke_stop_hook_fallback(monitor.workdir, task_path, log_path)
                else:
                    log_event(
                        log_path,
                        "INFO",
                        "follow-up prompt visible but task not marked done yet",
                        task_id=current_task_id,
                    )
        else:
            followup_seen_at = None
        if getattr(monitor, "result_status", None) == "success":
            if not task_path.exists():
                return "completed"
            if getattr(monitor, "result_seen_at", None) and (time.time() - monitor.result_seen_at) >= 10.0:
                if not fallback_invoked or (time.time() - fallback_last_attempt) >= 5.0:
                    log_event(log_path, "WARN", "result success observed; invoking stop-hook fallback")
                    fallback_last_attempt = time.time()
                    fallback_invoked = invoke_stop_hook_fallback(monitor.workdir, task_path, log_path)
                if not task_path.exists():
                    return "completed"
                if hard_cleanup_after_success(task_path, log_path):
                    return "completed"

        if monitor.proc.poll() is not None:
            returncode = int(monitor.proc.returncode or 0)
            if returncode == 0:
                log_event(log_path, "WARN", "agent exited with code 0 while task still active; attempting cleanup")
                if not fallback_invoked or (time.time() - fallback_last_attempt) >= 5.0:
                    fallback_last_attempt = time.time()
                    fallback_invoked = invoke_stop_hook_fallback(monitor.workdir, task_path, log_path)
                if not task_path.exists() or hard_cleanup_after_success(task_path, log_path):
                    return "completed"
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
) -> str:
    start_time = time.time()
    followup_seen_at: Optional[float] = None
    followup_enter_sent = False
    followup_ctrlc_sent = False
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
        monitor.maybe_report()
        if stop_on_followup_prompt and getattr(monitor, "ui_followup_prompt", False):
            if followup_seen_at is None:
                followup_seen_at = time.time()
                log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            seen_for = time.time() - followup_seen_at
            if seen_for >= 10.0 and not followup_enter_sent:
                followup_enter_sent = True
                monitor.send_keys(["Enter"], label=f"{label}:followup:enter")
            if seen_for >= 20.0 and not followup_ctrlc_sent:
                followup_ctrlc_sent = True
                monitor.send_keys(["C-C"], label=f"{label}:followup:ctrlc")
            if seen_for >= 40.0:
                log_event(log_path, "WARN", "follow-up prompt stuck; forcing phase end", label=label)
                return "followup_stuck"
        else:
            followup_seen_at = None
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
