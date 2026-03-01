#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import faulthandler
import signal
import sys
import threading
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

ORC_ROOT = Path(__file__).resolve().parents[1]
ORC_LOG_DIR = ORC_ROOT / ".orc"
ORC_LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_DIR = Path(tempfile.gettempdir()) / "orc"
DEBUG_LOG_PREFIX = "orc-debug"
DEBUG_ENV_TRUE_VALUES = {"1", "true", "yes"}
_DEBUG_ENABLED = False
_DEBUG_LOG_PATH: Optional[Path] = None
_DEBUG_SESSION_ID = f"{int(time.time() * 1000)}-{os.getpid()}"
_DEBUG_WORKDIR = ""
_LOG_WORKDIR = ""
_CRASH_HANDLERS_INSTALLED = False
_CRASH_HANDLER_LOCK = threading.Lock()
_FAULT_HANDLER_STREAM = None

ORC_LOG_NAME = "orc.log"
ORC_DATA_DIR = ".orc"
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"


def _min_log_level() -> int:
    level = os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip()
    return LOG_LEVELS.get(level, LOG_LEVELS[DEFAULT_LOG_LEVEL])


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _env_debug_enabled() -> bool:
    return os.environ.get("ORC_DEBUG_LOG", "0").lower().strip() in DEBUG_ENV_TRUE_VALUES


def _build_debug_log_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEBUG_LOG_DIR / f"{DEBUG_LOG_PREFIX}-{ts}-{os.getpid()}.jsonl"


def _write_debug_payload(payload: Dict[str, object]) -> None:
    global _DEBUG_LOG_PATH
    if _DEBUG_LOG_PATH is None:
        _DEBUG_LOG_PATH = _build_debug_log_path()
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def init_debug_logging(*, enabled: bool, workdir: str = "") -> Optional[Path]:
    global _DEBUG_ENABLED, _DEBUG_WORKDIR
    should_enable = bool(enabled or _env_debug_enabled())
    if not should_enable:
        return None
    if _DEBUG_ENABLED:
        return _DEBUG_LOG_PATH
    _DEBUG_ENABLED = True
    _DEBUG_WORKDIR = workdir
    _write_debug_payload(
        {
            "type": "debug_session_started",
            "sessionId": _DEBUG_SESSION_ID,
            "timestamp": int(time.time() * 1000),
            "workdir": workdir,
            "pid": os.getpid(),
            "logPath": str(_DEBUG_LOG_PATH) if _DEBUG_LOG_PATH else "",
        }
    )
    return _DEBUG_LOG_PATH


def get_debug_log_path() -> Optional[Path]:
    return _DEBUG_LOG_PATH


def set_log_context(*, workdir: str = "") -> None:
    global _LOG_WORKDIR
    resolved = str(workdir or "").strip()
    if not resolved:
        _LOG_WORKDIR = ""
        return
    try:
        _LOG_WORKDIR = str(Path(resolved).resolve())
    except Exception:
        _LOG_WORKDIR = resolved


def log_event(log_path: Path, level: str, message: str, **fields: object) -> None:
    min_level = _min_log_level()
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    context: Dict[str, object] = {"pid": pid, "orc_pid": pid}
    if _LOG_WORKDIR:
        context["workspace"] = _LOG_WORKDIR
    payload = {
        "ts": now_iso(),
        "level": level,
        "message": message,
        **context,
        **fields,
    }
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\n")


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
        # Best effort only: crash reporting must never recurse into another crash.
        pass
    return payload


def install_crash_handlers(
    *,
    entrypoint: str,
    phase: str,
    workspace: str,
    log_path: Path,
) -> None:
    global _CRASH_HANDLERS_INSTALLED, _FAULT_HANDLER_STREAM
    if _CRASH_HANDLERS_INSTALLED:
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

    def _signal_handler(signum, _frame) -> None:
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
        raise SystemExit(128 + int(signum))

    sys.excepthook = _sys_excepthook
    threading.excepthook = _threading_excepthook
    for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _signal_handler)
        except Exception:
            continue
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _FAULT_HANDLER_STREAM = log_path.open("a", encoding="utf-8", errors="replace")
        faulthandler.enable(file=_FAULT_HANDLER_STREAM, all_threads=True)
    except Exception:
        _FAULT_HANDLER_STREAM = None
    _CRASH_HANDLERS_INSTALLED = True


def debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, object]) -> None:
    if not _DEBUG_ENABLED:
        init_debug_logging(enabled=False)
    if not _DEBUG_ENABLED:
        return
    payload = {
        "type": "debug_event",
        "sessionId": _DEBUG_SESSION_ID,
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "workdir": _DEBUG_WORKDIR,
        "pid": os.getpid(),
    }
    _write_debug_payload(payload)
