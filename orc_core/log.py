#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core event logging — shared across all layers.

This module lives at the orc_core root so that domain, application,
and infrastructure layers can all import it without violating the
Dependency Rule. Infrastructure-specific logging (debug, crash handlers)
stays in infra/io/logging.py.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"


class _LogContext:
    """Module-level logging context (workspace for log enrichment)."""
    __slots__ = ("log_workdir",)

    def __init__(self) -> None:
        self.log_workdir: str = ""


_ctx = _LogContext()


def set_log_context(*, workdir: str = "") -> None:
    resolved = str(workdir or "").strip()
    if not resolved:
        _ctx.log_workdir = ""
        return
    try:
        _ctx.log_workdir = str(Path(resolved).resolve())
    except Exception:
        _ctx.log_workdir = resolved


def _min_log_level() -> int:
    level = os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip()
    return LOG_LEVELS.get(level, LOG_LEVELS[DEFAULT_LOG_LEVEL])


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def now_ms() -> int:
    return int(time.time() * 1000)


def log_event(log_path: Path, level: str, message: str, **fields: object) -> None:
    min_level = _min_log_level()
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    context: Dict[str, object] = {"pid": pid, "orc_pid": pid}
    if _ctx.log_workdir:
        context["workspace"] = _ctx.log_workdir
    payload = {
        "ts": now_iso(),
        "level": level,
        "message": message,
        **context,
        **fields,
    }
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\n")
