#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight checks before task execution (main integration validation)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .request import TaskExecutionResult
    from .runtime import _ExecutionContext

from ...infra.io.debug_log import debug_log
from ...infra.failure_reasons import build_main_integration_preflight_reason
from ...log import log_event
from ...git.git_helpers import classify_main_integration_error
from ...git.worktree_flow import preflight_main_integration
from .request import TaskExecutionResult
from ...models.task_status import TaskExecutionStatus

_logger = logging.getLogger(__name__)


def preflight_integration(
    log_path, ctx: _ExecutionContext,
) -> Optional[TaskExecutionResult]:
    """Check main integration prerequisites. Returns failure result or None."""
    request = ctx.request
    if not request.integrate_to_main:
        return None
    preflight = preflight_main_integration(base_workdir=request.base_workdir, main_branch=request.main_branch)
    failure_kind = classify_main_integration_error(preflight.error)
    safe_tracked = tuple(getattr(preflight, "safe_tracked", ()) or ())
    safe_untracked = tuple(getattr(preflight, "safe_untracked", ()) or ())
    unsafe_tracked = tuple(getattr(preflight, "unsafe_tracked", ()) or ())
    unsafe_untracked = tuple(getattr(preflight, "unsafe_untracked", ()) or ())
    debug_log(
        "MI1",
        "orc_core/task_execution.py:TaskExecutionEngine.execute",
        "main integration preflight evaluated",
        {
            "task_id": ctx.task_id,
            "base_workdir": request.base_workdir,
            "main_branch": request.main_branch,
            "ok": preflight.ok,
            "failure_kind": failure_kind,
            "error": preflight.error,
            "safe_tracked": list(safe_tracked[:20]),
            "safe_untracked": list(safe_untracked[:20]),
            "unsafe_tracked": list(unsafe_tracked[:20]),
            "unsafe_untracked": list(unsafe_untracked[:20]),
        },
    )
    if not preflight.ok:
        log_event(
            log_path,
            "ERROR",
            "main integration preflight failed",
            task_id=ctx.task_id,
            branch=request.main_branch,
            base_workdir=request.base_workdir,
            integration_failure_kind=failure_kind,
            error=preflight.error[:500],
            safe_tracked=list(safe_tracked[:20]),
            safe_untracked=list(safe_untracked[:20]),
            unsafe_tracked=list(unsafe_tracked[:20]),
            unsafe_untracked=list(unsafe_untracked[:20]),
        )
        _logger.error(
            f"❌ Невозможно подготовить интеграцию в {request.main_branch}: {preflight.error}"
        )
        ctx.ts_exec.result = "failed"
        ctx.ts_exec.reason = f"main_integration_preflight_failed:{failure_kind}"
        return TaskExecutionResult(
            status=TaskExecutionStatus.FAILED,
            reason=build_main_integration_preflight_reason(failure_kind, preflight.error),
        )
    return None
