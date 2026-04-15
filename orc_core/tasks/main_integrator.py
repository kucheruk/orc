#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main branch integration logic extracted from task_execution_finalize."""

from __future__ import annotations

import logging
from typing import Optional

from ..git.git_helpers import classify_main_integration_error, has_commits_ahead_of_branch
from ..log import log_event
from ..observability import timeline_step
from ..text_parse import SafeDict
from ..git.worktree_flow import get_head_commit, integrate_commit_into_main
from .task_agent_phases import run_merge_expert_phase
from .execution.request import TaskExecutionResult
from .execution.runtime import _ExecutionContext
from ..models.task_status import TaskExecutionStatus
from .task_state import delete_runtime_state_file

_logger = logging.getLogger(__name__)


def handle_main_integration(
    engine, ctx: _ExecutionContext, current_task_id: str, current_task_text: str,
    current_tag: str, effective_agent_output_log_path, timeline_id: str,
    restart_count: int, commit_completed: bool,
) -> Optional[TaskExecutionResult]:
    """Run main integration if requested. Returns result on failure, None on success/skip."""

    request = ctx.request
    ts_exec = ctx.ts_exec

    if not request.integrate_to_main:
        return None

    with timeline_step(
        timeline_id=timeline_id,
        task_id=current_task_id,
        step="main_integration",
        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
        attempt=restart_count + 1,
        data={"branch": request.main_branch},
    ) as ts_integ:
        if not has_commits_ahead_of_branch(request.workdir, request.main_branch, engine.log_path):
            log_event(
                engine.log_path,
                "INFO",
                "main integration skipped: no task commit ahead of main",
                task_id=current_task_id,
                branch=request.main_branch,
            )
            try:
                request.task_path.unlink(missing_ok=True)
                delete_runtime_state_file(request.task_path, engine.log_path, reason="task_completed")
            except OSError:
                pass
            ts_integ.result = "skipped"
            ts_integ.reason = "no_commits_ahead"
            return TaskExecutionResult(status=TaskExecutionStatus.COMPLETED, committed=commit_completed)
        try:
            commit_sha = get_head_commit(request.workdir)
        except (OSError, ValueError) as exc:
            log_event(
                engine.log_path,
                "ERROR",
                "cannot resolve task commit sha before main integration",
                task_id=current_task_id,
                error=str(exc),
            )
            _logger.error("❌ Не удалось определить commit задачи для переноса в main.")
            ts_integ.result = "failed"
            ts_integ.reason = "integration_commit_sha_failed"
            ts_exec.result = "failed"
            ts_exec.reason = "integration_commit_sha_failed"
            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="integration_commit_sha_failed")

        integration = integrate_commit_into_main(
            base_workdir=request.base_workdir,
            commit_sha=commit_sha,
            task_id=current_task_id,
            log_path=engine.log_path,
            main_branch=request.main_branch,
        )
        if not integration.ok and integration.conflict:
            merge_prompt_vars = SafeDict(
                task_text=current_task_text,
                task_id=current_task_id,
                backlog=request.backlog_arg,
                workspace=request.base_workdir,
            )
            if not run_merge_expert_phase(
                engine.worker,
                request,
                merge_prompt_vars,
                current_task_id,
                current_tag,
                engine.log_path,
                effective_agent_output_log_path,
                timeline_id,
                restart_count,
            ):
                ts_integ.result = "failed"
                ts_integ.reason = "merge_expert_phase_failed"
                ts_exec.result = "failed"
                ts_exec.reason = "merge_expert_phase_failed"
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="merge_expert_phase_failed")
            integration = integrate_commit_into_main(
                base_workdir=request.base_workdir,
                commit_sha=commit_sha,
                task_id=current_task_id,
                log_path=engine.log_path,
                main_branch=request.main_branch,
            )
        if not integration.ok:
            failure_kind = classify_main_integration_error(integration.error)
            log_event(
                engine.log_path,
                "ERROR",
                "failed to integrate task commit into main",
                task_id=current_task_id,
                commit_sha=commit_sha,
                integration_failure_kind=failure_kind,
                error=integration.error[:500],
            )
            _logger.error(f"❌ Не удалось перенести commit в {request.main_branch}: {integration.error}")
            ts_integ.result = "failed"
            ts_integ.reason = f"main_integration_failed:{failure_kind}"
            ts_exec.result = "failed"
            ts_exec.reason = f"main_integration_failed:{failure_kind}"
            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="main_integration_failed")
    return None
