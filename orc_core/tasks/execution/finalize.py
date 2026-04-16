#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finalization and stage completion orchestrator.

Delegates to focused modules:
- main_integrator: cherry-pick integration into main branch
- backlog_validator: backlog invariant checks
- stage_verdict_handlers: Strategy pattern for review/testing verdicts
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ...log import log_event
from ...observability import debug_log
from ...quit_signal import is_quit_after_task_requested
from ..backlog.validator import validate_backlog_invariant
from ..integration.main_integrator import handle_main_integration
from ..stages.artifacts import parse_stage_artifact_status, validate_stage_artifact_output
from ..stages.verdicts import VERDICT_HANDLERS, _StageCompletionInfo
from ..stages.phases import run_commit_phase
from .helpers import (
    _is_fragmented_summary_lines,
    _normalize_fragmented_summary_text,
    _update_completion_stats,
)
from .request import TaskExecutionResult
from .runtime import _ExecutionContext
from ..status import TaskExecutionStatus
from ...text_parse import SafeDict, clean_summary_lines

_logger = logging.getLogger(__name__)


def _collect_completion_stats(log_path: Path, task_id: str, request, monitor) -> None:
    """Log completion stats, clean summary, write metrics."""
    log_event(log_path, "INFO", "task completed", task_id=task_id)
    raw_summary_text = monitor.get_summary_text()
    raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
    cleaned_lines = clean_summary_lines(raw_lines)
    if _is_fragmented_summary_lines(cleaned_lines):
        summary_text = _normalize_fragmented_summary_text("\n".join(cleaned_lines))
    else:
        summary_text = "\n".join(cleaned_lines[-request.timing.summary_lines:])
    tokens = monitor.metrics.tokens_total if monitor.metrics.tokens_total is not None else "-"
    files_edited = monitor.metrics.files_edited if monitor.metrics.files_edited is not None else "-"
    _logger.info(
        f"[orc] completed stats tokens={tokens} lines={monitor.metrics.total_lines} "
        f"commands={monitor.metrics.command_count} files_edited={files_edited}"
    )
    _update_completion_stats(
        monitor=monitor, task_id=task_id, task_path=request.task_path,
        workdir=request.base_workdir or request.workdir, log_path=log_path,
        writer=request.state_writer, paths=request.state_paths,
    )
    debug_log("H8", "orc_core/task_execution.py:execute:summary", "summary prepared", {
        "summary_len": len(summary_text),
        "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
    })


def finalize_completed(
    engine,
    ctx: _ExecutionContext,
    current_task_id: str,
    current_task_text: str,
    current_tag: str,
    monitor,
) -> TaskExecutionResult:
    """Handle post-completion: stats, commit phase, main integration, backlog sync."""

    request = ctx.request
    effective_agent_output_log_path = ctx.effective_agent_output_log_path
    timeline_id = ctx.timeline_id
    ts_exec = ctx.ts_exec
    restart_count = ctx.restart_count
    base_backlog_path = ctx.base_backlog_path
    runtime_backlog_path = ctx.runtime_backlog_path

    commit_completed = False
    _collect_completion_stats(engine.log_path, current_task_id, request, monitor)
    prompt_vars = SafeDict(
        task_text=current_task_text,
        task_id=current_task_id,
        backlog=request.backlog_arg,
        workspace=request.workdir,
    )
    force_commit_for_quit_after_task = bool((not request.commit_phase) and is_quit_after_task_requested())
    should_run_commit_phase = bool(request.commit_phase or force_commit_for_quit_after_task)
    if force_commit_for_quit_after_task:
        log_event(
            engine.log_path,
            "INFO",
            "commit phase forced by quit-after-task request",
            task_id=current_task_id,
        )
        _logger.info("[orc] commit phase: forced by QUIT AFTER TASK")
    if should_run_commit_phase and not run_commit_phase(
        engine.worker,
        request,
        prompt_vars,
        current_task_id,
        current_tag,
        engine.log_path,
        effective_agent_output_log_path,
        timeline_id,
        restart_count,
    ):
        _logger.error("❌ Commit phase failed. Stop to avoid accumulating uncommitted changes.")
        ts_exec.result = "failed"
        ts_exec.reason = "commit_phase_failed"
        return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="commit_phase_failed")
    if should_run_commit_phase:
        commit_completed = True

    integration_result = handle_main_integration(
        engine, ctx, current_task_id, current_task_text, current_tag,
        effective_agent_output_log_path, timeline_id, restart_count, commit_completed,
    )
    if integration_result is not None:
        return integration_result

    # Kanban mode uses _board sentinel — card state is the source of truth, skip backlog invariant
    if base_backlog_path.name != "_board" and not base_backlog_path.is_dir():
        invariant_failure = validate_backlog_invariant(engine, ctx, current_task_id, base_backlog_path, runtime_backlog_path, ts_exec)
        if invariant_failure is not None:
            return invariant_failure

    # Clean up task state files (previously done by stop hook)
    try:
        request.task_path.unlink(missing_ok=True)
        request.state_writer.delete_runtime_state(request.task_path, engine.log_path, reason="task_completed")
    except OSError:
        pass
    return TaskExecutionResult(status=TaskExecutionStatus.COMPLETED, committed=commit_completed)


def complete_stage(
    engine,
    ctx: _ExecutionContext,
    *,
    current_task_id: str,
    current_task_text: str,
    current_tag: str,
    current_monitor,
    current_stage_id: str,
    current_stage_index: int,
    current_stage_is_final: bool,
    current_attempt_number: int,
    current_ts_attempt,
    completion_reason: str = "",
) -> tuple[Optional[TaskExecutionResult], Optional[int], bool]:
    """Validate stage artifact and determine next stage.
    Returns (failure_result, next_stage_index, is_final_completed).
    """
    enforce_stage_artifacts = ctx.enforce_stage_artifacts
    stage_specs = ctx.stage_specs
    artifact_bundle = ctx.artifact_bundle
    ts_exec = ctx.ts_exec

    if enforce_stage_artifacts:
        artifact_ok, artifact_reason, artifact_path = validate_stage_artifact_output(
            stage_id=current_stage_id,
            bundle=artifact_bundle,
        )
        if not artifact_ok:
            failure_reason = f"stage_artifact_{current_stage_id}_{artifact_reason}"
            log_event(
                engine.log_path,
                "ERROR",
                "sdlc stage artifact validation failed",
                task_id=current_task_id,
                stage_id=current_stage_id,
                stage_index=current_stage_index + 1,
                stage_total=len(stage_specs),
                artifact_path=str(artifact_path),
                artifact_reason=artifact_reason,
            )
            _logger.error(
                "❌ SDLC stage завершился без валидного артефакта: "
                f"{current_stage_id} -> {artifact_path}"
            )
            current_ts_attempt.result = "failed"
            current_ts_attempt.reason = failure_reason
            ts_exec.result = "failed"
            ts_exec.reason = failure_reason
            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None, False

    # Validate stage status header for stages that require it
    if enforce_stage_artifacts and current_stage_id in VERDICT_HANDLERS:
        status_ok, stage_status, stage_status_reason, stage_status_path = parse_stage_artifact_status(
            stage_id=current_stage_id,
            bundle=artifact_bundle,
        )
        if not status_ok:
            failure_reason = f"stage_artifact_{current_stage_id}_{stage_status_reason}"
            log_event(
                engine.log_path,
                "ERROR",
                "sdlc stage status parsing failed",
                task_id=current_task_id,
                stage_id=current_stage_id,
                stage_index=current_stage_index + 1,
                stage_total=len(stage_specs),
                artifact_path=str(stage_status_path),
                artifact_reason=stage_status_reason,
                artifact_status=stage_status,
            )
            _logger.error(
                "❌ SDLC stage артефакт не содержит валидный `status:` заголовок: "
                f"{current_stage_id} -> {stage_status_path}"
            )
            current_ts_attempt.result = "failed"
            current_ts_attempt.reason = failure_reason
            ts_exec.result = "failed"
            ts_exec.reason = failure_reason
            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None, False

    current_ts_attempt.result = "completed"
    if completion_reason:
        current_ts_attempt.reason = completion_reason
    if current_stage_is_final:
        return None, None, True

    next_stage_index = current_stage_index + 1

    # Dispatch to stage-specific verdict handler (Strategy pattern)
    if enforce_stage_artifacts and current_stage_id in VERDICT_HANDLERS:
        info = _StageCompletionInfo(
            engine=engine, ctx=ctx, current_task_id=current_task_id,
            current_stage_id=current_stage_id, current_stage_index=current_stage_index,
            current_ts_attempt=current_ts_attempt,
        )
        handler = VERDICT_HANDLERS[current_stage_id]
        failure_result, redirect_index = handler(info)
        if failure_result is not None:
            return failure_result, None, False
        if redirect_index is not None:
            next_stage_index = redirect_index

    log_event(
        engine.log_path,
        "INFO",
        "sdlc stage completed",
        task_id=current_task_id,
        stage_id=current_stage_id,
        stage_index=current_stage_index + 1,
        stage_total=len(stage_specs),
        next_stage_index=(next_stage_index + 1) if next_stage_index is not None else None,
        completion_reason=completion_reason or "monitor_completed",
    )
    return None, next_stage_index, False
