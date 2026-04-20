#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from ...log import log_event
from ...observability import debug_log, timeline_step
from ...text_parse import SafeDict
from ...agents.results.io import RESULT_FILE_ENV, RESULT_RUN_ID_ENV
from ..backlog.detector import check_backlog_done as _check_backlog_done
from ..completion.handlers import COMPLETION_HANDLERS
from ..integration.task_file import update_task_restart_count
from ..stages.artifacts import build_stage_artifact_bundle
from ..backlog.source import MarkdownTaskSource
from ..status import TaskCompletionStatus, TaskExecutionStatus
from ..ports import GitDiffProbe
from .attempt_env import build_attempt_agent_env
from .finalize import complete_stage as _complete_stage, finalize_completed as _finalize_completed
from .helpers import _find_first_stage_index, _record_attempt_tokens, _write_prompt_file
from .launch import launch_and_wait
from .request import LaunchConfig, TaskExecutionResult
from .restart_policy import RestartPolicy
from .runtime import _ExecutionContext, _ResumeState
from .stage import TaskStageSpec

if TYPE_CHECKING:
    from .engine import TaskExecutionEngine

_logger = logging.getLogger(__name__)


def _default_git_diff_probe() -> GitDiffProbe:
    from ...git.task_adapters import DEFAULT_GIT_DIFF_PROBE
    return DEFAULT_GIT_DIFF_PROBE


def prepare_stages(ctx: _ExecutionContext) -> None:
    """Initialize stage specs and artifact bundle."""
    request = ctx.request
    stage_specs = list(request.stage_specs)
    if not stage_specs:
        stage_specs = [TaskStageSpec(
            stage_id="implementation",
            model=request.models.model,
            prompt_template=request.templates.prompt_template,
            is_pre_rendered=True,
        )]
    ctx.stage_specs = stage_specs
    ctx.artifact_bundle = build_stage_artifact_bundle(workdir=request.workdir, task_id=ctx.task_id)
    ctx.enforce_stage_artifacts = bool(request.enforce_stage_artifacts) and bool(request.stage_specs)
    ctx.implementation_stage_index = _find_first_stage_index(stage_specs, "implementation")
    ctx.feedback_iteration_count = 0


def run_stage_loop(engine: "TaskExecutionEngine", ctx: _ExecutionContext, resume: _ResumeState) -> TaskExecutionResult:
    """Execute stages in sequence with restart/retry logic."""
    request = ctx.request
    stage_specs = ctx.stage_specs
    enforce_stage_artifacts = ctx.enforce_stage_artifacts
    task_id = ctx.task_id
    task_text = ctx.task_text
    timeline_id = ctx.timeline_id
    ts_exec = ctx.ts_exec
    effective_agent_output_log_path = ctx.effective_agent_output_log_path
    effective_agent_env = ctx.effective_agent_env
    artifact_prompt_vars = dict(ctx.artifact_bundle.to_prompt_vars())
    log_path = engine.log_path
    restart_policy = RestartPolicy(max_restarts=request.timing.max_restarts)

    stage_index = 0
    while stage_index < len(stage_specs):
        stage_spec = stage_specs[stage_index]
        stage_id = (stage_spec.stage_id or f"stage_{stage_index + 1}").strip()
        stage_model = (stage_spec.model or request.models.model).strip() or request.models.model
        stage_is_final = stage_index == (len(stage_specs) - 1)
        if stage_spec.is_pre_rendered:
            prompt = stage_spec.prompt_template
        else:
            prompt_vars = SafeDict(
                task_text=task_text,
                task_id=task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
                stage_id=stage_id,
                stage_index=stage_index + 1,
                stage_total=len(stage_specs),
                stage_is_final=stage_is_final,
                **artifact_prompt_vars,
            )
            prompt = stage_spec.prompt_template.format_map(prompt_vars)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
        tag = f"{ts}__{safe_name}__{stage_id}"
        prompt_path = _write_prompt_file(request.run_root, prompt, tag)

        stage_resume_existing = resume.resume_existing and stage_index == 0
        stage_resume_id = resume.resume_id if stage_resume_existing else None
        resume_prompt_text = request.timing.nudge_text if stage_resume_existing else None
        restart_count = resume.persisted_restart_count if stage_resume_existing else 0
        elapsed_before_start_stage = resume.elapsed_before_start if stage_resume_existing else 0.0

        stage_next_index: Optional[int] = None
        missing_artifact_retry_budget = 1
        while True:
            attempt_number = restart_count + 1
            with timeline_step(
                timeline_id=timeline_id,
                task_id=task_id,
                step="agent_attempt",
                location="orc_core/task_execution.py:_run_stage_loop",
                attempt=attempt_number,
                data={"restart_count": restart_count, "stage_id": stage_id, "stage_index": stage_index + 1},
            ) as ts_attempt:
                update_task_restart_count(request.task_path, log_path, restart_count, writer=request.state_writer)
                log_event(
                    log_path,
                    "INFO",
                    "launching agent",
                    task_id=task_id,
                    restart_count=restart_count,
                    stage_id=stage_id,
                    stage_index=stage_index + 1,
                    stage_total=len(stage_specs),
                )
                try:
                    attempt_agent_env = build_attempt_agent_env(
                        effective_agent_env,
                        run_root=request.run_root,
                        task_id=task_id,
                        stage_id=stage_id,
                        attempt=attempt_number,
                    )
                    ctx.last_agent_result_file = attempt_agent_env.get(RESULT_FILE_ENV, "")
                    ctx.last_agent_run_id = attempt_agent_env.get(RESULT_RUN_ID_ENV, "")
                    launch_cfg = LaunchConfig(
                        workdir=request.workdir,
                        prompt_path=prompt_path,
                        model=stage_model,
                        log_path=log_path,
                        report_interval=request.timing.report_interval,
                        summary_lines=request.timing.summary_lines,
                        task_id=f"{task_id} [{stage_id}]" if stage_id else task_id,
                        progress_done=request.progress_done,
                        progress_total=request.progress_total,
                        progress_in_progress=request.progress_in_progress,
                        agent_output_log_path=effective_agent_output_log_path,
                        agent_env=attempt_agent_env,
                        snapshot_publisher=request.snapshot_publisher,
                        resume_id=stage_resume_id,
                        resume_latest=False,
                        resume_prompt=resume_prompt_text if stage_resume_existing else None,
                        timeline_id=timeline_id,
                        attempt=attempt_number,
                        backlog_task_lister=lambda p: MarkdownTaskSource(p).list_tasks(),
                        git_diff_fn=_default_git_diff_probe().get_numstat,
                    )
                    active_monitor, result = launch_and_wait(
                        engine.worker, ctx, launch_cfg, log_path,
                        notify=engine.notify,
                        backlog_query=engine.backlog_query,
                        elapsed_before_start=elapsed_before_start_stage,
                        ignore_initial_backlog_done=enforce_stage_artifacts and stage_index > 0,
                        attempt_number=attempt_number,
                    )
                    # Persist tokens as soon as the attempt ends — even on
                    # restart/stall/TTL — so looping cards don't hide their
                    # real cost from the teamlead and budget checks.
                    _record_attempt_tokens(
                        monitor=active_monitor,
                        task_id=task_id,
                        workdir=request.base_workdir or request.workdir,
                        log_path=log_path,
                        writer=request.state_writer,
                        paths=request.state_paths,
                    )
                except FileNotFoundError:
                    _logger.error("agent not found")
                    ts_attempt.result = "failed"
                    ts_attempt.reason = "agent_not_found"
                    ts_exec.result = "failed"
                    ts_exec.reason = "agent_not_found"
                    return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="agent_not_found")

                if result == TaskCompletionStatus.COMPLETED:
                    stage_failure, stage_next_index, stage_completed_final = _complete_stage(
                        engine, ctx,
                        current_task_id=task_id,
                        current_task_text=task_text,
                        current_tag=tag,
                        current_monitor=active_monitor,
                        current_stage_id=stage_id,
                        current_stage_index=stage_index,
                        current_stage_is_final=stage_is_final,
                        current_attempt_number=attempt_number,
                        current_ts_attempt=ts_attempt,
                    )
                    if stage_failure is not None:
                        return stage_failure
                    if stage_completed_final:
                        ctx.restart_count = restart_count
                        return _finalize_completed(engine, ctx, task_id, task_text, tag, active_monitor)
                    break
                handler = COMPLETION_HANDLERS.get(result)
                if handler is not None:
                    action = handler.handle(
                        task_id=task_id, stage_model=stage_model,
                        restart_count=restart_count, request=request,
                        log_path=log_path, timeline_id=timeline_id,
                        attempt_number=attempt_number,
                        ts_attempt=ts_attempt, ts_exec=ts_exec,
                    )
                    if action.action == "return" and action.result is not None:
                        return action.result
                # Backlog done detection for non-completed results
                done_action, done_result, done_next_index, missing_artifact_retry_budget = _check_backlog_done(
                    engine,
                    ctx,
                    result=result,
                    stage_id=stage_id,
                    stage_index=stage_index,
                    stage_is_final=stage_is_final,
                    attempt_number=attempt_number,
                    ts_attempt=ts_attempt,
                    tag=tag,
                    active_monitor=active_monitor,
                    restart_count=restart_count,
                    missing_artifact_retry_budget=missing_artifact_retry_budget,
                )
                if done_action == "return":
                    return done_result
                if done_action == "break":
                    stage_next_index = done_next_index
                    break

                restart_count += 1
                ts_attempt.result = "restart"
                ts_attempt.reason = result
            if restart_policy.exceeded(restart_count):
                log_event(log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                from ...signals import SignalKind, emit_signal
                emit_signal(
                    SignalKind.ATTEMPT_MAX_RESTARTS,
                    "restart_policy_exceeded",
                    task_id=task_id,
                    context={"restart_count": restart_count,
                             "max_restarts": restart_policy.max_restarts,
                             "stage_id": stage_id},
                )
                debug_log(
                    "H6",
                    "orc_core/task_execution.py:_run_stage_loop:max_restarts",
                    "max restarts exceeded",
                    {"task_id": task_id, "restart_count": restart_count, "max_restarts": restart_policy.max_restarts},
                )
                _logger.error("max restarts exceeded for task %s", task_id)
                ts_exec.result = "failed"
                ts_exec.reason = "max_restarts_exceeded"
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="max_restarts_exceeded")
            log_event(log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
            reason_text = restart_policy.reason_text(result)
            continue_vars = SafeDict(
                task_text=task_text,
                task_id=task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
                stage_id=stage_id,
                stage_index=stage_index + 1,
                stage_total=len(stage_specs),
                stage_is_final=stage_is_final,
                reason=reason_text,
                restart_count=restart_count,
                max_restarts=request.timing.max_restarts,
            )
            prompt = request.templates.continue_template.format_map(continue_vars)
            prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__r{restart_count}")
            resume_prompt_text = prompt
            stage_resume_id = None  # fresh prompt, don't resume stale conversation
            delay = restart_policy.backoff_seconds(restart_count)
            log_event(log_path, "INFO", "restart backoff", task_id=task_id, restart_count=restart_count, delay_seconds=delay)
            with timeline_step(
                timeline_id=timeline_id,
                task_id=task_id,
                step="restart_backoff_sleep",
                location="orc_core/task_execution.py:_run_stage_loop",
                attempt=attempt_number,
                data={"delay_seconds": delay},
            ) as ts_backoff:
                time.sleep(delay)
        if stage_next_index is None:
            break
        stage_index = stage_next_index

    ts_exec.result = "failed"
    ts_exec.reason = "no_final_stage_completion"
    return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="no_final_stage_completion")
