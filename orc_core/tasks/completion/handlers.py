#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completion status handlers — extensible registry replacing if/elif chain."""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from ...log import log_event
from ...observability import timeline_instant
from ..integration.task_file import update_task_restart_count
from ..execution.request import TaskExecutionResult
from ..status import TaskCompletionStatus, TaskExecutionStatus

_logger = logging.getLogger(__name__)


class CompletionAction:
    """Result of a completion handler: what the stage loop should do next."""
    __slots__ = ("action", "result", "delay_seconds")

    def __init__(self, action: str, result: Optional[TaskExecutionResult] = None, delay_seconds: float = 0.0):
        self.action = action  # "return" | "continue" (restart loop)
        self.result = result
        self.delay_seconds = delay_seconds


class CompletionHandler(Protocol):
    def handle(self, *, task_id: str, stage_model: str, restart_count: int,
               request, log_path, timeline_id: str, attempt_number: int,
               ts_attempt, ts_exec) -> CompletionAction: ...


class ModelUnavailableHandler:
    """Retry "Cannot use this model" with exponential backoff.

    `agent --list-models` flaps between "Available models: ..." and "No
    models available for this account" on the cursor service even within
    the same minute — the error surfaces when the wrapper's session-level
    model cache is cold against a throttled / partially-degraded cursor
    backend. The previous behavior (hard-fail on first occurrence) treated
    a transient server glitch as a permanent configuration error and
    dumped the task's attempt.

    Going through the normal restart path means this flap consumes the
    shared restart budget (request.timing.max_restarts, default 2), and
    we pre-sleep the attempt so the next retry is spaced far enough apart
    for a transient cursor degradation to clear.
    """

    _INITIAL_BACKOFF_SECONDS = 20.0
    _BACKOFF_MULTIPLIER = 2.0
    _MAX_BACKOFF_SECONDS = 120.0

    def handle(self, *, task_id, stage_model, restart_count, request, log_path,
               timeline_id, attempt_number, ts_attempt, ts_exec, **kw) -> CompletionAction:
        delay = min(
            self._INITIAL_BACKOFF_SECONDS * (self._BACKOFF_MULTIPLIER ** max(restart_count, 0)),
            self._MAX_BACKOFF_SECONDS,
        )
        log_event(log_path, "WARN",
                  "agent model unavailable; will retry after backoff",
                  task_id=task_id, model=stage_model,
                  restart_count=restart_count,
                  max_restarts=request.timing.max_restarts,
                  delay_seconds=delay)
        _logger.warning(
            "⚠️ cursor вернул 'Cannot use this model: %s' (restart %d/%d). "
            "Пауза %.0fs — обычно это транзиентный glitch cursor backend.",
            stage_model, restart_count + 1, request.timing.max_restarts, delay,
        )
        timeline_instant(
            timeline_id=timeline_id, task_id=task_id,
            step="model_unavailable_backoff",
            location="orc_core/completion/handlers.py",
            attempt=attempt_number,
            result="continue", reason="model_unavailable_retry",
            data={"delay_seconds": delay, "restart_count": restart_count},
        )
        # Sleep here so the outer stage_loop's subsequent short
        # RestartPolicy backoff lands on top of this longer pause.
        import time as _time
        _time.sleep(delay)
        ts_attempt.result = "restart"
        ts_attempt.reason = "model_unavailable_retry"
        return CompletionAction("continue")


class WaitingForInputHandler:
    def handle(self, *, task_id, stage_model, restart_count, request, log_path,
               timeline_id, attempt_number, ts_attempt, ts_exec, **kw) -> CompletionAction:
        ts_attempt.result = "waiting_for_input"
        restart_count += 1
        update_task_restart_count(request.task_path, log_path, restart_count, writer=request.state_writer)
        log_event(log_path, "INFO", "waiting_for_input_budget_tick",
                  task_id=task_id, restart_count=restart_count,
                  max_restarts=request.timing.max_restarts)
        if restart_count > request.timing.max_restarts:
            log_event(log_path, "ERROR", "max restarts exceeded while waiting for input",
                      task_id=task_id, restart_count=restart_count,
                      max_restarts=request.timing.max_restarts)
            _logger.error("❌ Агент зациклился на запросе follow-up ввода. Лимит перезапусков исчерпан.")
            ts_exec.result = "failed"
            ts_exec.reason = "max_restarts_exceeded"
            return CompletionAction("return", TaskExecutionResult(
                status=TaskExecutionStatus.FAILED, reason="max_restarts_exceeded"))
        delay = max(request.timing.nudge_cooldown, request.timing.poll, 1.0)
        timeline_instant(
            timeline_id=timeline_id, task_id=task_id,
            step="restart_backoff_sleep",
            location="orc_core/completion_handlers.py",
            attempt=attempt_number,
            result="continue", reason="waiting_for_input",
            data={"delay_seconds": delay},
        )
        _logger.warning(
            f"[orc] агент запросил follow-up ввод; продолжу цикл через {delay:.1f}s "
            "(resume сохранен, задача не потеряна)"
        )
        ts_exec.result = "continue"
        ts_exec.reason = "waiting_for_input"
        return CompletionAction("return", TaskExecutionResult(
            status=TaskExecutionStatus.CONTINUE, reason="waiting_for_input", delay_seconds=delay))


COMPLETION_HANDLERS: dict[TaskCompletionStatus, CompletionHandler] = {
    TaskCompletionStatus.MODEL_UNAVAILABLE: ModelUnavailableHandler(),
    TaskCompletionStatus.WAITING_FOR_INPUT: WaitingForInputHandler(),
}
