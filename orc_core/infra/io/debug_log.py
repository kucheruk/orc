#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug logging: structured JSON debug events and debug-mode logging."""

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

from .logging import (
    DEBUG_MODE_LOG_PATH,
    DEBUG_MODE_SESSION_ID,
    _cfg,
    _env_debug_enabled,
    _write_debug_payload,
)


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
