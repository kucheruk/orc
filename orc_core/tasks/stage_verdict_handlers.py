#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strategy pattern for handling SDLC stage verdicts (review, testing).

Each handler inspects the stage artifact status and returns:
- (None, next_stage_index) on success/redirect
- (TaskExecutionResult, None) on failure

Register new stage handlers in VERDICT_HANDLERS to extend without modifying
the complete_stage() orchestrator (OCP).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from ..log import log_event
from .stage_artifacts import parse_stage_artifact_status
from .execution.request import TaskExecutionResult
from .execution.runtime import _ExecutionContext
from .execution.stage import SDLC_FEEDBACK_MAX_ITERATIONS
from .task_status_types import TaskExecutionStatus

_logger = logging.getLogger(__name__)

# Type alias for verdict handlers
VerdictHandler = Callable[
    ["_StageCompletionInfo"],
    tuple[Optional[TaskExecutionResult], Optional[int]],
]


class _StageCompletionInfo:
    """Bundle of data passed to verdict handlers."""
    __slots__ = (
        "engine", "ctx", "current_task_id", "current_stage_id",
        "current_stage_index", "stage_specs", "artifact_bundle",
        "implementation_stage_index", "current_ts_attempt", "ts_exec",
    )

    def __init__(self, engine, ctx: _ExecutionContext, current_task_id: str,
                 current_stage_id: str, current_stage_index: int, current_ts_attempt):
        self.engine = engine
        self.ctx = ctx
        self.current_task_id = current_task_id
        self.current_stage_id = current_stage_id
        self.current_stage_index = current_stage_index
        self.stage_specs = ctx.stage_specs
        self.artifact_bundle = ctx.artifact_bundle
        self.implementation_stage_index = ctx.implementation_stage_index
        self.current_ts_attempt = current_ts_attempt
        self.ts_exec = ctx.ts_exec


def _handle_review_verdict(info: _StageCompletionInfo) -> tuple[Optional[TaskExecutionResult], Optional[int]]:
    """Review stage: 'needs_changes' loops back to implementation."""
    status_ok, stage_status, _reason, _path = parse_stage_artifact_status(
        stage_id=info.current_stage_id,
        bundle=info.artifact_bundle,
    )
    if not (status_ok and stage_status == "needs_changes"):
        return None, None  # no redirect

    info.ctx.feedback_iteration_count += 1
    if info.ctx.feedback_iteration_count > SDLC_FEEDBACK_MAX_ITERATIONS:
        failure_reason = "sdlc_feedback_limit_exceeded"
        log_event(
            info.engine.log_path,
            "ERROR",
            "sdlc feedback iteration limit exceeded",
            task_id=info.current_task_id,
            stage_id=info.current_stage_id,
            stage_index=info.current_stage_index + 1,
            stage_total=len(info.stage_specs),
            feedback_iteration_count=info.ctx.feedback_iteration_count,
            max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
        )
        _logger.error("❌ SDLC feedback loop превысил лимит итераций.")
        info.ts_exec.result = "failed"
        info.ts_exec.reason = failure_reason
        return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None

    if info.implementation_stage_index is None:
        failure_reason = "sdlc_feedback_missing_implementation_stage"
        log_event(
            info.engine.log_path,
            "ERROR",
            "sdlc feedback loop requested but implementation stage missing",
            task_id=info.current_task_id,
            stage_id=info.current_stage_id,
            stage_index=info.current_stage_index + 1,
            stage_total=len(info.stage_specs),
        )
        _logger.error("❌ SDLC feedback loop не может вернуться: отсутствует stage `implementation`.")
        info.ts_exec.result = "failed"
        info.ts_exec.reason = failure_reason
        return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None

    next_stage_index = info.implementation_stage_index
    log_event(
        info.engine.log_path,
        "INFO",
        "sdlc feedback loop requested by review verdict",
        task_id=info.current_task_id,
        stage_id=info.current_stage_id,
        stage_index=info.current_stage_index + 1,
        stage_total=len(info.stage_specs),
        next_stage_id=info.stage_specs[next_stage_index].stage_id,
        next_stage_index=next_stage_index + 1,
        feedback_iteration_count=info.ctx.feedback_iteration_count,
        max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
    )
    return None, next_stage_index


def _handle_testing_verdict(info: _StageCompletionInfo) -> tuple[Optional[TaskExecutionResult], Optional[int]]:
    """Testing stage: 'fail' verdict fails the task."""
    status_ok, stage_status, _reason, _path = parse_stage_artifact_status(
        stage_id=info.current_stage_id,
        bundle=info.artifact_bundle,
    )
    if not (status_ok and stage_status == "fail"):
        return None, None  # pass through

    failure_reason = "testing_failed"
    log_event(
        info.engine.log_path,
        "ERROR",
        "testing stage reported failure verdict",
        task_id=info.current_task_id,
        stage_id=info.current_stage_id,
        stage_index=info.current_stage_index + 1,
        stage_total=len(info.stage_specs),
    )
    _logger.error("❌ Testing stage завершился с verdict `status: fail`.")
    info.ts_exec.result = "failed"
    info.ts_exec.reason = failure_reason
    return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None


# Registry: stage_id → verdict handler
# Add new handlers here to extend without modifying complete_stage()
VERDICT_HANDLERS: dict[str, VerdictHandler] = {
    "review": _handle_review_verdict,
    "testing": _handle_testing_verdict,
}
