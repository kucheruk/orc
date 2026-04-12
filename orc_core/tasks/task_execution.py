#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re

_logger = logging.getLogger(__name__)
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..infra.backend import Backend as BackendProtocol

from .hooks import update_task_restart_count
from ..log import log_event
from ..infra.io.debug_log import debug_log
from ..infra.io.timeline import timeline_instant, timeline_step
from ..quit_signal import is_stop_requested
from .task_status_types import TaskCompletionStatus, TaskExecutionStatus
from .supervisor_lifecycle import wait_for_completion
from .stage_artifacts import build_stage_artifact_bundle
from .task_state import runtime_state_path
from ..text_parse import SafeDict
from .task_execution_preflight import preflight_integration
from .task_execution_resume import recover_resume_state, init_task_file
from .task_source import MarkdownTaskSource
from ..git.git_helpers import git_diff_numstat

from .task_status_types import RESTART_REASON_TEXT
from .task_execution_types import (
    LaunchConfig,
    TaskStageSpec,
    TaskExecutionRequest,
    TaskExecutionResult,
    _ExecutionContext,
    _ResumeState,
    TaskWorker,
    AgentTaskWorker,
)

from .task_execution_helpers import (
    _restart_backoff_seconds,
    _write_prompt_file,
    _build_agent_output_log_path,
    _resolve_runtime_backlog_path,
    _find_first_stage_index,
)

from .backlog_detector import check_backlog_done as _check_backlog_done
from .task_agent_phases import cleanup_monitor_processes as _cleanup_monitor_processes
from .task_execution_finalize import (
    finalize_completed as _finalize_completed,
    complete_stage as _complete_stage,
)
from .task_execution_launch import launch_and_wait
from .completion_handlers import COMPLETION_HANDLERS







class TaskExecutionEngine:
    def __init__(self, *, worker: Optional[TaskWorker] = None, log_path: Path, backend: Optional["BackendProtocol"] = None) -> None:
        self.worker = worker or AgentTaskWorker(backend=backend)
        self.log_path = log_path

    def execute(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        task_id = request.task.task_id
        timeline_id = f"{task_id}-{uuid.uuid4().hex[:8]}"
        with timeline_step(
            timeline_id=timeline_id,
            task_id=task_id,
            step="task_execute",
            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
            data={"workdir": request.workdir},
        ) as ts_exec:
            return self._execute_inner(request, task_id, timeline_id, ts_exec)

    def _execute_inner(self, request: TaskExecutionRequest, task_id: str, timeline_id: str, ts_exec) -> TaskExecutionResult:
        task_text = request.task.text
        base_backlog_path = request.backlog_path
        runtime_backlog_path = _resolve_runtime_backlog_path(request)
        task_runtime_path = runtime_state_path(request.task_path)
        effective_agent_env = dict(request.agent_env or {})
        effective_agent_env.setdefault("ORC_TASK_RUNTIME_FILE", str(task_runtime_path))
        effective_agent_output_log_path = request.agent_output_log_path or _build_agent_output_log_path(request.run_root, task_id)
        worktree_path_value = request.workdir if Path(request.workdir).resolve() != Path(request.base_workdir).resolve() else ""
        log_event(self.log_path, "INFO", "agent output log selected", task_id=task_id, agent_output_log_path=effective_agent_output_log_path)
        log_event(self.log_path, "INFO", "backlog resolution", task_id=task_id, base_backlog_path=str(base_backlog_path), runtime_backlog_path=str(runtime_backlog_path))

        ctx = _ExecutionContext(
            request=request, task_id=task_id, task_text=task_text,
            timeline_id=timeline_id, ts_exec=ts_exec,
            effective_agent_output_log_path=effective_agent_output_log_path,
            base_backlog_path=base_backlog_path, runtime_backlog_path=runtime_backlog_path,
            effective_agent_env=effective_agent_env, worktree_path_value=worktree_path_value,
        )

        preflight_failure = preflight_integration(self.log_path, ctx)
        if preflight_failure:
            return preflight_failure

        resume = _ResumeState()
        resume_failure = recover_resume_state(self.log_path, ctx, resume)
        if resume_failure:
            return resume_failure

        init_task_file(self.log_path, ctx, resume)
        _prepare_stages(ctx)
        return _run_stage_loop(self, ctx, resume)

    async def execute_async(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        return await asyncio.to_thread(self.execute, request)


# ── Standalone phase functions ──────────────────────────────────


def _prepare_stages(ctx: _ExecutionContext) -> None:
    """Initialize stage specs and artifact bundle."""
    request = ctx.request
    stage_specs = list(request.stage_specs)
    if not stage_specs:
        stage_specs = [TaskStageSpec(stage_id="implementation", model=request.models.model, prompt_template=request.templates.prompt_template)]
    ctx.stage_specs = stage_specs
    ctx.artifact_bundle = build_stage_artifact_bundle(workdir=request.workdir, task_id=ctx.task_id)
    ctx.enforce_stage_artifacts = bool(request.enforce_stage_artifacts) and bool(request.stage_specs)
    ctx.implementation_stage_index = _find_first_stage_index(stage_specs, "implementation")
    ctx.feedback_iteration_count = 0


def _run_stage_loop(engine: TaskExecutionEngine, ctx: _ExecutionContext, resume: _ResumeState) -> TaskExecutionResult:
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

    stage_index = 0
    while stage_index < len(stage_specs):
        stage_spec = stage_specs[stage_index]
        stage_id = (stage_spec.stage_id or f"stage_{stage_index + 1}").strip()
        stage_model = (stage_spec.model or request.models.model).strip() or request.models.model
        stage_is_final = stage_index == (len(stage_specs) - 1)
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
                update_task_restart_count(request.task_path, log_path, restart_count)
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
                        agent_env=effective_agent_env,
                        snapshot_publisher=request.snapshot_publisher,
                        resume_id=stage_resume_id,
                        resume_latest=False,
                        resume_prompt=resume_prompt_text if stage_resume_existing else None,
                        timeline_id=timeline_id,
                        attempt=attempt_number,
                        backlog_task_lister=lambda p: MarkdownTaskSource(p).list_tasks(),
                        git_diff_fn=git_diff_numstat,
                    )
                    active_monitor, result = launch_and_wait(
                        engine.worker, ctx, launch_cfg, log_path,
                        elapsed_before_start=elapsed_before_start_stage,
                        ignore_initial_backlog_done=enforce_stage_artifacts and stage_index > 0,
                        attempt_number=attempt_number,
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
            if restart_count > request.timing.max_restarts:
                log_event(log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                debug_log(
                    "H6",
                    "orc_core/task_execution.py:_run_stage_loop:max_restarts",
                    "max restarts exceeded",
                    {"task_id": task_id, "restart_count": restart_count, "max_restarts": request.timing.max_restarts},
                )
                _logger.error("max restarts exceeded for task %s", task_id)
                ts_exec.result = "failed"
                ts_exec.reason = "max_restarts_exceeded"
                return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="max_restarts_exceeded")
            log_event(log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
            reason_text = RESTART_REASON_TEXT.get(result, result)
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
            delay = _restart_backoff_seconds(restart_count)
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
