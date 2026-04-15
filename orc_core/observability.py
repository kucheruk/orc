#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observability seam — use cases depend on this module, not on concrete infra/io modules.

Defines DebugLogger and Timeline Protocols plus default singletons that delegate to the
existing infra.io implementations. Callers that need structured debug events or timeline
tracing should import from here:

    from orc_core.observability import debug_log, timeline_instant, timeline_step

Callers that want to inject a mock for tests should depend on DebugLogger / Timeline.
"""

from __future__ import annotations

from typing import Any, ContextManager, Dict, Optional, Protocol

from .infra.io.debug_log import debug_log, debug_mode_log  # re-export
from .infra.io.timeline import (  # re-export
    timeline_instant,
    timeline_step,
    timeline_step_finished,
    timeline_step_started,
)

__all__ = [
    "DebugLogger",
    "Timeline",
    "debug_log",
    "debug_mode_log",
    "timeline_instant",
    "timeline_step",
    "timeline_step_started",
    "timeline_step_finished",
    "default_debug_logger",
    "default_timeline",
]


class DebugLogger(Protocol):
    """Port for structured debug events. Default impl delegates to infra.io.debug_log."""
    def log(self, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None: ...


class Timeline(Protocol):
    """Port for timeline tracing. Default impl delegates to infra.io.timeline."""

    def instant(
        self, *,
        timeline_id: str, task_id: str, step: str, location: str,
        attempt: int = 0, hypothesis_id: str = "TL",
        result: str = "", reason: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> int: ...

    def step(
        self, *,
        timeline_id: str, task_id: str, step: str, location: str,
        attempt: int = 0, hypothesis_id: str = "TL",
        data: Optional[Dict[str, Any]] = None,
    ) -> ContextManager[Any]: ...


class _DefaultDebugLogger:
    def log(self, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
        debug_log(hypothesis_id, location, message, data)


class _DefaultTimeline:
    def instant(self, **kwargs: Any) -> int:
        return timeline_instant(**kwargs)

    def step(self, **kwargs: Any) -> ContextManager[Any]:
        return timeline_step(**kwargs)


default_debug_logger: DebugLogger = _DefaultDebugLogger()
default_timeline: Timeline = _DefaultTimeline()
