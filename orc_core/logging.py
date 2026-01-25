#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

ORC_ROOT = Path(__file__).resolve().parents[1]
ORC_LOG_DIR = ORC_ROOT / ".orc"
ORC_LOG_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG_PATH = ORC_LOG_DIR / "debug.log"
DEBUG_RAW_LOG_PATH = ORC_LOG_DIR / "debug-raw.log"

ORC_LOG_NAME = "orc.log"
ORC_DATA_DIR = ".orc"
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"


def _min_log_level() -> int:
    level = os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip()
    return LOG_LEVELS.get(level, LOG_LEVELS[DEFAULT_LOG_LEVEL])


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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
    if os.environ.get("ORC_DEBUG_LOG", "0").lower() not in {"1", "true", "yes"}:
        return
    payload = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
