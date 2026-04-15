#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completion status handlers — extensible registry replacing if/elif chain."""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from ..log import log_event
from ..observability import timeline_instant
from .hooks import update_task_restart_count
from .execution.request import TaskExecutionResult
from .task_status import TaskCompletionStatus, TaskExecutionStatus

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
    def handle(self, *, task_id, stage_model, restart_count, request, log_path,
               timeline_id, attempt_number, ts_attempt, ts_exec, **kw) -> CompletionAction:
        log_event(log_path, "ERROR", "agent model unavailable; stopping without restart",
                  task_id=task_id, model=stage_model)
        _logger.error(
            "❌ Выбранная модель недоступна для `agent`. "
            "Проверьте `agent --list-models` и укажите доступную модель через `--model`."
        )
        ts_attempt.result = "failed"
        ts_attempt.reason = "model_unavailable"
        ts_exec.result = "failed"
        ts_exec.reason = "model_unavailable"
        return CompletionAction("return", TaskExecutionResult(
            status=TaskExecutionStatus.FAILED, reason="model_unavailable"))


class WaitingForInputHandler:
    def handle(self, *, task_id, stage_model, restart_count, request, log_path,
               timeline_id, attempt_number, ts_attempt, ts_exec, **kw) -> CompletionAction:
        ts_attempt.result = "waiting_for_input"
        restart_count += 1
        update_task_restart_count(request.task_path, log_path, restart_count)
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
