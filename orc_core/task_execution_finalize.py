#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extracted finalization and stage completion logic from TaskExecutionEngine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .git_helpers import classify_main_integration_error, has_commits_ahead_of_branch
from .logging import debug_log, log_event, timeline_step
from .quit_signal import is_quit_after_task_requested
from .stage_artifacts import parse_stage_artifact_status, validate_stage_artifact_output
from .task_agent_phases import run_commit_phase, run_merge_expert_phase
from .task_execution_helpers import (
    _is_fragmented_summary_lines,
    _normalize_fragmented_summary_text,
    _should_defer_base_backlog_sync_to_integration,
    _sync_done_task_from_runtime_to_base,
    _update_completion_stats,
)
from .task_execution_types import (
    SDLC_FEEDBACK_MAX_ITERATIONS,
    TaskExecutionResult,
    TaskExecutionStatus,
    _ExecutionContext,
)
from .task_state import delete_runtime_state_file
from .text_parse import SafeDict, clean_summary_lines
from .worktree_flow import get_head_commit, integrate_commit_into_main

_logger = logging.getLogger(__name__)


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
    log_event(engine.log_path, "INFO", "task completed", task_id=current_task_id)
    raw_summary_text = monitor.get_summary_text()
    raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
    cleaned_lines = clean_summary_lines(raw_lines)
    if _is_fragmented_summary_lines(cleaned_lines):
        summary_text = _normalize_fragmented_summary_text("\n".join(cleaned_lines))
    else:
        summary_text = "\n".join(cleaned_lines[-request.timing.summary_lines :])
    tokens = monitor.metrics.tokens_total if monitor.metrics.tokens_total is not None else "-"
    files_edited = monitor.metrics.files_edited if monitor.metrics.files_edited is not None else "-"
    _logger.info(
        f"[orc] completed stats tokens={tokens} lines={monitor.metrics.total_lines} "
        f"commands={monitor.metrics.command_count} files_edited={files_edited}"
    )
    _update_completion_stats(
        monitor=monitor,
        task_id=current_task_id,
        task_path=request.task_path,
        workdir=request.workdir,
        log_path=engine.log_path,
    )
    debug_log(
        "H8",
        "orc_core/task_execution.py:execute:summary",
        "summary prepared",
        {
            "summary_len": len(summary_text),
            "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
        },
    )
    # Kanban session manager handles its own notifications
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

    integration_result = _handle_main_integration(
        engine, ctx, current_task_id, current_task_text, current_tag,
        effective_agent_output_log_path, timeline_id, restart_count, commit_completed,
    )
    if integration_result is not None:
        return integration_result

    # Kanban mode uses _board sentinel — card state is the source of truth, skip backlog invariant
    if base_backlog_path.name != "_board" and not base_backlog_path.is_dir():
        invariant_failure = _validate_backlog_invariant(engine, ctx, current_task_id, base_backlog_path, runtime_backlog_path, ts_exec)
        if invariant_failure is not None:
            return invariant_failure

    # Clean up task state files (previously done by stop hook)
    try:
        request.task_path.unlink(missing_ok=True)
        delete_runtime_state_file(request.task_path, engine.log_path, reason="task_completed")
    except OSError:
        pass
    return TaskExecutionResult(status=TaskExecutionStatus.COMPLETED, committed=commit_completed)


def _handle_main_integration(
    engine, ctx, current_task_id, current_task_text, current_tag,
    effective_agent_output_log_path, timeline_id, restart_count, commit_completed,
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


def _validate_backlog_invariant(engine, ctx, current_task_id, base_backlog_path, runtime_backlog_path, ts_exec) -> Optional[TaskExecutionResult]:
    """Ensure base backlog reflects done state after completion. Returns failure result or None."""
    request = ctx.request
    try:
        from .task_source import MarkdownTaskSource

        base_done = MarkdownTaskSource(base_backlog_path).is_task_done(current_task_id)
        runtime_done = False
        if runtime_backlog_path != base_backlog_path:
            runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(current_task_id)
        if runtime_done and not base_done:
            if _should_defer_base_backlog_sync_to_integration(
                integrate_to_main=request.integrate_to_main,
                base_backlog_path=base_backlog_path,
                runtime_backlog_path=runtime_backlog_path,
            ):
                log_event(
                    engine.log_path,
                    "ERROR",
                    "backlog invariant violated after main integration: task marked done only in runtime worktree backlog",
                    task_id=current_task_id,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                    integrate_to_main=request.integrate_to_main,
                )
                debug_log(
                    "MI2",
                    "orc_core/task_execution.py:TaskExecutionEngine.execute",
                    "base backlog was not updated by integrated commit",
                    {
                        "task_id": current_task_id,
                        "base_backlog_path": str(base_backlog_path),
                        "runtime_backlog_path": str(runtime_backlog_path),
                    },
                )
                _logger.error(
                    "❌ После успешной main integration backlog в base не отмечен как done. "
                    "Значит, отметка попала не в task commit, а пыталась догнаться позже."
                )
                ts_exec.result = "failed"
                ts_exec.reason = "worktree_not_integrated_to_base"
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="worktree_not_integrated_to_base")
            synced = _sync_done_task_from_runtime_to_base(
                task_id=current_task_id,
                base_backlog_path=base_backlog_path,
                runtime_backlog_path=runtime_backlog_path,
                log_path=engine.log_path,
            )
            if not synced:
                log_event(
                    engine.log_path,
                    "WARN",
                    "backlog sync to base failed (likely race with concurrent integration); "
                    "integration step will reconcile",
                    task_id=current_task_id,
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                )
    except (OSError, ValueError) as exc:
        log_event(
            engine.log_path,
            "ERROR",
            "failed to validate backlog invariant after completion",
            task_id=current_task_id,
            error=str(exc),
            base_backlog_path=str(base_backlog_path),
            runtime_backlog_path=str(runtime_backlog_path),
        )
    return None


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
    implementation_stage_index = ctx.implementation_stage_index
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
    if enforce_stage_artifacts and current_stage_id in {"review", "testing"}:
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
    if enforce_stage_artifacts and current_stage_id == "review":
        status_ok, stage_status, _stage_status_reason, _stage_status_path = parse_stage_artifact_status(
            stage_id=current_stage_id,
            bundle=artifact_bundle,
        )
        if status_ok and stage_status == "needs_changes":
            ctx.feedback_iteration_count += 1
            if ctx.feedback_iteration_count > SDLC_FEEDBACK_MAX_ITERATIONS:
                failure_reason = "sdlc_feedback_limit_exceeded"
                log_event(
                    engine.log_path,
                    "ERROR",
                    "sdlc feedback iteration limit exceeded",
                    task_id=current_task_id,
                    stage_id=current_stage_id,
                    stage_index=current_stage_index + 1,
                    stage_total=len(stage_specs),
                    feedback_iteration_count=ctx.feedback_iteration_count,
                    max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
                )
                _logger.error("❌ SDLC feedback loop превысил лимит итераций.")
                ts_exec.result = "failed"
                ts_exec.reason = failure_reason
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None, False
            if implementation_stage_index is None:
                failure_reason = "sdlc_feedback_missing_implementation_stage"
                log_event(
                    engine.log_path,
                    "ERROR",
                    "sdlc feedback loop requested but implementation stage missing",
                    task_id=current_task_id,
                    stage_id=current_stage_id,
                    stage_index=current_stage_index + 1,
                    stage_total=len(stage_specs),
                )
                _logger.error("❌ SDLC feedback loop не может вернуться: отсутствует stage `implementation`.")
                ts_exec.result = "failed"
                ts_exec.reason = failure_reason
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None, False
            next_stage_index = implementation_stage_index
            log_event(
                engine.log_path,
                "INFO",
                "sdlc feedback loop requested by review verdict",
                task_id=current_task_id,
                stage_id=current_stage_id,
                stage_index=current_stage_index + 1,
                stage_total=len(stage_specs),
                next_stage_id=stage_specs[next_stage_index].stage_id,
                next_stage_index=next_stage_index + 1,
                feedback_iteration_count=ctx.feedback_iteration_count,
                max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
            )
    if enforce_stage_artifacts and current_stage_id == "testing":
        status_ok, stage_status, _stage_status_reason, _stage_status_path = parse_stage_artifact_status(
            stage_id=current_stage_id,
            bundle=artifact_bundle,
        )
        if status_ok and stage_status == "fail":
            failure_reason = "testing_failed"
            log_event(
                engine.log_path,
                "ERROR",
                "testing stage reported failure verdict",
                task_id=current_task_id,
                stage_id=current_stage_id,
                stage_index=current_stage_index + 1,
                stage_total=len(stage_specs),
            )
            _logger.error("❌ Testing stage завершился с verdict `status: fail`.")
            ts_exec.result = "failed"
            ts_exec.reason = failure_reason
            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason=failure_reason), None, False
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
