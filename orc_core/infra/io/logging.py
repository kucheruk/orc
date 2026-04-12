#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core logging: log_event and shared logging config/utilities.

Debug logging → debug_log.py
Timeline tracing → timeline.py
Crash handlers → crash_handler.py
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..state.state_paths import resolve_state_root

ORC_ROOT = Path(__file__).resolve().parents[2]
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
