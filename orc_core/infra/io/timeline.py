#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Timeline tracing: structured start/finish/instant events for task execution."""

import os
import time
from contextlib import contextmanager
from typing import Dict, Optional

from .debug_log import init_debug_logging
from .logging import _cfg, _write_debug_payload, now_ms


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


class _TimelineStepContext:
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
