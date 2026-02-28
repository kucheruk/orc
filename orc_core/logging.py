#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

ORC_ROOT = Path(__file__).resolve().parents[1]
ORC_LOG_DIR = ORC_ROOT / ".orc"
ORC_LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_DIR = Path("/tmp/orc")
DEBUG_LOG_PREFIX = "orc-debug"
DEBUG_ENV_TRUE_VALUES = {"1", "true", "yes"}
_DEBUG_ENABLED = False
_DEBUG_LOG_PATH: Optional[Path] = None
_DEBUG_SESSION_ID = f"{int(time.time() * 1000)}-{os.getpid()}"
_DEBUG_WORKDIR = ""

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


def log_event(log_path: Path, level: str, message: str, **fields: object) -> None:
    min_level = _min_log_level()
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": now_iso(),
        "level": level,
        "message": message,
        **fields,
    }
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\n")


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
