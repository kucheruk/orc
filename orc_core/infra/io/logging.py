#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Infrastructure logging: debug logging, crash handlers, log directories.

Core event logging (log_event, now_iso, now_ms) lives in orc_core.log
so that all layers can use it without depending on infra/.
This module re-exports them for backward compatibility during migration,
and adds infrastructure-specific debug/crash logging.
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ...persistence.state_paths import resolve_state_root

# Re-export from shared log module so existing infra-internal imports still work
from ...log import (  # noqa: F401
    LOG_LEVELS,
    DEFAULT_LOG_LEVEL,
    log_event,
    now_iso,
    now_ms,
    set_log_context,
)

ORC_ROOT = Path(__file__).resolve().parents[2]
ORC_LOG_DIR = resolve_state_root() / "logs"
ORC_LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_DIR = Path(tempfile.gettempdir()) / "orc"
DEBUG_LOG_PREFIX = "orc-debug"
DEBUG_ENV_TRUE_VALUES = {"1", "true", "yes"}


class _LoggingConfig:
    """Module-level logging state for debug/crash logging."""
    __slots__ = (
        "debug_enabled", "debug_log_path", "debug_session_id",
        "debug_workdir", "crash_handlers_installed",
        "fault_handler_stream",
    )

    def __init__(self) -> None:
        self.debug_enabled: bool = False
        self.debug_log_path: Optional[Path] = None
        self.debug_session_id: str = f"{int(time.time() * 1000)}-{os.getpid()}"
        self.debug_workdir: str = ""
        self.crash_handlers_installed: bool = False
        self.fault_handler_stream: object = None


_cfg = _LoggingConfig()
_CRASH_HANDLER_LOCK = threading.Lock()

ORC_LOG_NAME = "orc.log"
ORC_DATA_DIR = ".orc"
DEBUG_MODE_LOG_PATH = DEBUG_LOG_DIR / "debug-mode.log"
DEBUG_MODE_SESSION_ID = "debug-mode"


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
