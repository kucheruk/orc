#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crash handlers: sys.excepthook, threading.excepthook, signal handlers, faulthandler."""

import faulthandler
import json
import os
import signal
import sys
import threading
import traceback
from pathlib import Path
from typing import Dict

from ..infra.io.logging import _CRASH_HANDLER_LOCK, _cfg, log_event, now_iso


def build_crash_stdout_payload(
    *,
    entrypoint: str,
    phase: str,
    exception_type: str,
    error: str,
    traceback_text: str,
    workspace: str,
) -> Dict[str, object]:
    resolved_workspace = str(workspace or "").strip()
    if resolved_workspace:
        try:
            resolved_workspace = str(Path(resolved_workspace).resolve())
        except Exception:
            pass
    payload: Dict[str, object] = {
        "event": "orc_crash_report",
        "entrypoint": entrypoint,
        "phase": phase,
        "exception_type": exception_type,
        "error": error,
        "traceback": traceback_text,
        "workspace": resolved_workspace,
        "pid": os.getpid(),
        "ts": now_iso(),
    }
    return payload


def emit_crash_stdout_payload(
    *,
    entrypoint: str,
    phase: str,
    exception_type: str,
    error: str,
    traceback_text: str,
    workspace: str,
) -> Dict[str, object]:
    payload = build_crash_stdout_payload(
        entrypoint=entrypoint,
        phase=phase,
        exception_type=exception_type,
        error=error,
        traceback_text=traceback_text,
        workspace=workspace,
    )
    print(json.dumps(payload, ensure_ascii=False), file=sys.stdout, flush=True)
    return payload


def report_fatal_exception(
    *,
    entrypoint: str,
    phase: str,
    exception_type: str,
    error: str,
    traceback_text: str,
    workspace: str,
    log_path: Path,
    source: str,
) -> Dict[str, object]:
    payload = emit_crash_stdout_payload(
        entrypoint=entrypoint,
        phase=phase,
        exception_type=exception_type,
        error=error,
        traceback_text=traceback_text,
        workspace=workspace,
    )
    try:
        log_event(log_path, "ERROR", "fatal crash captured", source=source, **payload)
    except Exception:
        pass
    return payload


def install_crash_handlers(
    *,
    entrypoint: str,
    phase: str,
    workspace: str,
    log_path: Path,
) -> None:
    if _cfg.crash_handlers_installed:
        return

    def _emit(exc_type: str, error: str, tb_text: str, source: str) -> None:
        report_fatal_exception(
            entrypoint=entrypoint,
            phase=phase,
            exception_type=exc_type,
            error=error,
            traceback_text=tb_text,
            workspace=workspace,
            log_path=log_path,
            source=source,
        )

    def _sys_excepthook(exc_type, exc_value, exc_tb) -> None:
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        _emit(getattr(exc_type, "__name__", "Exception"), str(exc_value), tb_text, "sys.excepthook")

    def _threading_excepthook(args: threading.ExceptHookArgs) -> None:
        exc_type = args.exc_type
        exc_value = args.exc_value
        exc_tb = args.exc_traceback
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        type_name = getattr(exc_type, "__name__", "Exception")
        _emit(type_name, str(exc_value), tb_text, "threading.excepthook")

    _killpg_fired = False

    def _signal_handler(signum, _frame) -> None:
        nonlocal _killpg_fired
        if not _CRASH_HANDLER_LOCK.acquire(blocking=False):
            return
        try:
            try:
                sig_name = signal.Signals(signum).name
            except Exception:
                sig_name = str(signum)
            _emit("SignalExit", f"terminated by signal {sig_name}", "", "signal.handler")
        finally:
            _CRASH_HANDLER_LOCK.release()
        if not _killpg_fired:
            _killpg_fired = True
            from ..cli.cli_app import _terminate_child_process_groups
            from ..infra.process.process_groups import kill_own_process_group
            _terminate_child_process_groups()
            kill_own_process_group()
        raise SystemExit(128 + int(signum))

    sys.excepthook = _sys_excepthook
    threading.excepthook = _threading_excepthook
    for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT", "SIGINT"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except Exception:
            continue

    # SIGUSR1 — headless equivalent of the TUI 'q' hotkey: toggles
    # "finish current attempts, then quit" mode. Every running role
    # agent keeps running, but the teamlead and worker loops observe
    # is_quit_after_task_requested() between iterations and bail out
    # after their current card attempt finishes, then the orchestrator
    # exits cleanly. Sending it again clears the flag (idempotent).
    # Usage from an external supervisor:
    #     kill -USR1 <orc_pid>
    def _quit_after_task_handler(_signum, _frame) -> None:
        try:
            from ..quit_signal import toggle_quit_after_task
        except Exception:
            return
        try:
            now_on = toggle_quit_after_task()
        except Exception:
            return
        try:
            log_event(
                log_path, "WARN",
                "quit-after-task toggled via SIGUSR1",
                requested=bool(now_on),
            )
        except Exception:
            pass

    usr1 = getattr(signal, "SIGUSR1", None)
    if usr1 is not None:
        try:
            signal.signal(usr1, _quit_after_task_handler)
        except Exception:
            pass
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _cfg.fault_handler_stream = log_path.open("a", encoding="utf-8", errors="replace")
        faulthandler.enable(file=_cfg.fault_handler_stream, all_threads=True)
    except Exception:
        _cfg.fault_handler_stream = None
    _cfg.crash_handlers_installed = True
