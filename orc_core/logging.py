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
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .state_paths import resolve_state_root

ORC_ROOT = Path(__file__).resolve().parents[1]
ORC_LOG_DIR = resolve_state_root() / "logs"
ORC_LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_DIR = Path(tempfile.gettempdir()) / "orc"
DEBUG_LOG_PREFIX = "orc-debug"
DEBUG_ENV_TRUE_VALUES = {"1", "true", "yes"}
class _LoggingConfig:
    """Module-level logging state, replacing scattered globals."""
    __slots__ = (
        "debug_enabled", "debug_log_path", "debug_session_id",
        "debug_workdir", "log_workdir", "crash_handlers_installed",
        "fault_handler_stream",
    )

    def __init__(self) -> None:
        self.debug_enabled: bool = False
        self.debug_log_path: Optional[Path] = None
        self.debug_session_id: str = f"{int(time.time() * 1000)}-{os.getpid()}"
        self.debug_workdir: str = ""
        self.log_workdir: str = ""
        self.crash_handlers_installed: bool = False
        self.fault_handler_stream: object = None


_cfg = _LoggingConfig()
_CRASH_HANDLER_LOCK = threading.Lock()

ORC_LOG_NAME = "orc.log"
ORC_DATA_DIR = ".orc"
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"
DEBUG_MODE_LOG_PATH = DEBUG_LOG_DIR / "debug-mode.log"
DEBUG_MODE_SESSION_ID = "debug-mode"


def _min_log_level() -> int:
    level = os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip()
    return LOG_LEVELS.get(level, LOG_LEVELS[DEFAULT_LOG_LEVEL])


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def now_ms() -> int:
    return int(time.time() * 1000)


def _env_debug_enabled() -> bool:
    return os.environ.get("ORC_DEBUG_LOG", "0").lower().strip() in DEBUG_ENV_TRUE_VALUES


def _build_debug_log_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEBUG_LOG_DIR / f"{DEBUG_LOG_PREFIX}-{ts}-{os.getpid()}.jsonl"


def _write_debug_payload(payload: Dict[str, object]) -> None:
    if _cfg.debug_log_path is None:
        _cfg.debug_log_path = _build_debug_log_path()
    _cfg.debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    with _cfg.debug_log_path.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def init_debug_logging(*, enabled: bool, workdir: str = "") -> Optional[Path]:
    should_enable = bool(enabled or _env_debug_enabled())
    if not should_enable:
        return None
    if _cfg.debug_enabled:
        return _cfg.debug_log_path
    _cfg.debug_enabled = True
    _cfg.debug_workdir = workdir
    _write_debug_payload(
        {
            "type": "debug_session_started",
            "sessionId": _cfg.debug_session_id,
            "timestamp": int(time.time() * 1000),
            "workdir": workdir,
            "pid": os.getpid(),
            "logPath": str(_cfg.debug_log_path) if _cfg.debug_log_path else "",
        }
    )
    return _cfg.debug_log_path


def get_debug_log_path() -> Optional[Path]:
    return _cfg.debug_log_path


def set_log_context(*, workdir: str = "") -> None:
    resolved = str(workdir or "").strip()
    if not resolved:
        _cfg.log_workdir = ""
        return
    try:
        _cfg.log_workdir = str(Path(resolved).resolve())
    except Exception:
        _cfg.log_workdir = resolved


def log_event(log_path: Path, level: str, message: str, **fields: object) -> None:
    min_level = _min_log_level()
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    context: Dict[str, object] = {"pid": pid, "orc_pid": pid}
    if _cfg.log_workdir:
        context["workspace"] = _cfg.log_workdir
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
        _cfg.fault_handler_stream = log_path.open("a", encoding="utf-8", errors="replace")
        faulthandler.enable(file=_cfg.fault_handler_stream, all_threads=True)
    except Exception:
        _cfg.fault_handler_stream = None
    _cfg.crash_handlers_installed = True


def debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, object]) -> None:
    if not _cfg.debug_enabled:
        init_debug_logging(enabled=False)
    if not _cfg.debug_enabled:
        return
    payload = {
        "type": "debug_event",
        "sessionId": _cfg.debug_session_id,
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "workdir": _cfg.debug_workdir,
        "pid": os.getpid(),
    }
    _write_debug_payload(payload)


def debug_mode_log(run_id: str, hypothesis_id: str, location: str, message: str, data: Dict[str, object]) -> None:
    payload = {
        "sessionId": DEBUG_MODE_SESSION_ID,
        "runId": str(run_id or "run1"),
        "hypothesisId": str(hypothesis_id or ""),
        "location": str(location or ""),
        "message": str(message or ""),
        "data": data if isinstance(data, dict) else {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        DEBUG_MODE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_MODE_LOG_PATH.open("a", encoding="utf-8", errors="replace") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def _timeline_enabled() -> bool:
    if not _cfg.debug_enabled:
        init_debug_logging(enabled=False)
    return _cfg.debug_enabled


def _timeline_base_payload(
    *,
    timeline_id: str,
    task_id: str,
    step: str,
    attempt: int,
    location: str,
    hypothesis_id: str,
    timestamp_ms: int,
) -> Dict[str, object]:
    return {
        "type": "debug_timeline",
        "sessionId": _cfg.debug_session_id,
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "timeline_id": str(timeline_id or ""),
        "task_id": str(task_id or ""),
        "step": str(step or ""),
        "attempt": max(int(attempt), 0),
        "timestamp_ms": int(timestamp_ms),
        "workdir": _cfg.debug_workdir,
        "pid": os.getpid(),
    }


def timeline_step_started(
    *,
    timeline_id: str,
    task_id: str,
    step: str,
    location: str,
    attempt: int = 0,
    hypothesis_id: str = "TL",
    data: Optional[Dict[str, object]] = None,
    timestamp_ms: Optional[int] = None,
) -> int:
    ts_ms = int(timestamp_ms if isinstance(timestamp_ms, int) else now_ms())
    if not _timeline_enabled():
        return ts_ms
    payload = _timeline_base_payload(
        timeline_id=timeline_id,
        task_id=task_id,
        step=step,
        attempt=attempt,
        location=location,
        hypothesis_id=hypothesis_id,
        timestamp_ms=ts_ms,
    )
    payload["event"] = "start"
    if isinstance(data, dict) and data:
        payload["data"] = data
    _write_debug_payload(payload)
    return ts_ms


def timeline_step_finished(
    *,
    timeline_id: str,
    task_id: str,
    step: str,
    location: str,
    started_at_ms: int,
    result: str,
    attempt: int = 0,
    hypothesis_id: str = "TL",
    reason: str = "",
    data: Optional[Dict[str, object]] = None,
    timestamp_ms: Optional[int] = None,
) -> int:
    ts_ms = int(timestamp_ms if isinstance(timestamp_ms, int) else now_ms())
    if not _timeline_enabled():
        return ts_ms
    start_ms = int(started_at_ms if isinstance(started_at_ms, int) else ts_ms)
    payload = _timeline_base_payload(
        timeline_id=timeline_id,
        task_id=task_id,
        step=step,
        attempt=attempt,
        location=location,
        hypothesis_id=hypothesis_id,
        timestamp_ms=ts_ms,
    )
    payload["event"] = "finish"
    payload["started_at_ms"] = start_ms
    payload["duration_ms"] = max(ts_ms - start_ms, 0)
    payload["result"] = str(result or "")
    if reason:
        payload["reason"] = str(reason)
    if isinstance(data, dict) and data:
        payload["data"] = data
    _write_debug_payload(payload)
    return ts_ms


def timeline_instant(
    *,
    timeline_id: str,
    task_id: str,
    step: str,
    location: str,
    attempt: int = 0,
    hypothesis_id: str = "TL",
    result: str = "",
    reason: str = "",
    data: Optional[Dict[str, object]] = None,
    timestamp_ms: Optional[int] = None,
) -> int:
    ts_ms = int(timestamp_ms if isinstance(timestamp_ms, int) else now_ms())
    if not _timeline_enabled():
        return ts_ms
    payload = _timeline_base_payload(
        timeline_id=timeline_id,
        task_id=task_id,
        step=step,
        attempt=attempt,
        location=location,
        hypothesis_id=hypothesis_id,
        timestamp_ms=ts_ms,
    )
    payload["event"] = "instant"
    if result:
        payload["result"] = str(result)
    if reason:
        payload["reason"] = str(reason)
    if isinstance(data, dict) and data:
        payload["data"] = data
    _write_debug_payload(payload)
    return ts_ms


# ── Timeline step context manager ──────────────────────────────────


class _TimelineStepContext:
    """Mutable context yielded by ``timeline_step``.

    Callers set ``result`` and ``reason`` before exiting the ``with`` block.
    If ``result`` is not set explicitly, it defaults to ``"completed"`` on
    normal exit and ``"failed"`` on exception.
    """

    __slots__ = (
        "timeline_id", "task_id", "step", "location", "attempt",
        "hypothesis_id", "_started_ms", "result", "reason", "finish_data",
    )

    def __init__(
        self,
        *,
        timeline_id: str,
        task_id: str,
        step: str,
        location: str,
        attempt: int = 0,
        hypothesis_id: str = "TL",
    ) -> None:
        self.timeline_id = timeline_id
        self.task_id = task_id
        self.step = step
        self.location = location
        self.attempt = attempt
        self.hypothesis_id = hypothesis_id
        self._started_ms: int = 0
        self.result: str = ""
        self.reason: str = ""
        self.finish_data: Optional[Dict[str, object]] = None

    @property
    def started_at_ms(self) -> int:
        return self._started_ms


@contextmanager
def timeline_step(
    *,
    timeline_id: str,
    task_id: str,
    step: str,
    location: str,
    attempt: int = 0,
    hypothesis_id: str = "TL",
    data: Optional[Dict[str, object]] = None,
):
    """Context manager that auto-pairs timeline start/finish.

    Usage::

        with timeline_step(timeline_id=tid, task_id=tid, step="phase",
                           location="module:func") as ts:
            ...
            ts.result = "completed"
            ts.reason = "clean_tree"

    On normal exit ``result`` defaults to ``"completed"``.
    On exception ``result`` defaults to ``"failed"`` and the exception is re-raised.
    """
    ctx = _TimelineStepContext(
        timeline_id=timeline_id, task_id=task_id, step=step,
        location=location, attempt=attempt, hypothesis_id=hypothesis_id,
    )
    ctx._started_ms = timeline_step_started(
        timeline_id=timeline_id, task_id=task_id, step=step,
        location=location, attempt=attempt, hypothesis_id=hypothesis_id,
        data=data,
    )
    try:
        yield ctx
    except BaseException:
        if not ctx.result:
            ctx.result = "failed"
        timeline_step_finished(
            timeline_id=timeline_id, task_id=task_id, step=step,
            location=location, attempt=attempt, hypothesis_id=hypothesis_id,
            started_at_ms=ctx._started_ms, result=ctx.result,
            reason=ctx.reason, data=ctx.finish_data,
        )
        raise
    else:
        if not ctx.result:
            ctx.result = "completed"
        timeline_step_finished(
            timeline_id=timeline_id, task_id=task_id, step=step,
            location=location, attempt=attempt, hypothesis_id=hypothesis_id,
            started_at_ms=ctx._started_ms, result=ctx.result,
            reason=ctx.reason, data=ctx.finish_data,
        )
