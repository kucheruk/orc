#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import re

_logger = logging.getLogger(__name__)
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .backend import Backend as BackendProtocol

from .atomic_io import write_json_atomic
from .failure_reasons import build_main_integration_preflight_reason
from .git_helpers import classify_main_integration_error
from .hooks import update_task_restart_count, write_task_file
from .logging import debug_log, log_event, timeline_instant, timeline_step
from .quit_signal import is_stop_requested
from .session_state import save_active_session, save_session_manifest
from .task_execution_types import TaskCompletionStatus, TaskExecutionStatus
from .supervisor_lifecycle import wait_for_completion
from .stage_artifacts import build_stage_artifact_bundle
from .task_state import delete_runtime_state_file, read_task_active_seconds, runtime_state_path
from .text_parse import SafeDict
from .worktree_flow import preflight_main_integration

from .task_execution_types import (
    TaskStageSpec,
    TaskExecutionRequest,
    TaskExecutionResult,
    _ExecutionContext,
    _ResumeState,
    TaskWorker,
    AgentTaskWorker,
    RESTART_REASON_TEXT,
)

from .task_execution_helpers import (
    _restart_backoff_seconds,
    _write_prompt_file,
    _build_agent_output_log_path,
    _resolve_runtime_backlog_path,
    _sync_done_task_from_runtime_to_base,
    _should_defer_base_backlog_sync_to_integration,
    _find_first_stage_index,
)

from .task_agent_phases import (
    cleanup_monitor_processes as _cleanup_monitor_processes,
    should_retry_after_missing_stage_artifact as _should_retry_after_missing_stage_artifact,
)
from .task_execution_finalize import (
    finalize_completed as _finalize_completed,
    complete_stage as _complete_stage,
)







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

        preflight_failure = self._preflight_integration(ctx)
        if preflight_failure:
            return preflight_failure

        resume = _ResumeState()
        resume_failure = self._recover_resume_state(ctx, resume)
        if resume_failure:
            return resume_failure

        self._init_task_file(ctx, resume)
        self._prepare_stages(ctx)
        return self._run_stage_loop(ctx, resume)

    def _preflight_integration(self, ctx: _ExecutionContext) -> Optional[TaskExecutionResult]:
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
                self.log_path,
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

    def _recover_resume_state(self, ctx: _ExecutionContext, resume: _ResumeState) -> Optional[TaskExecutionResult]:
        """Recover state from existing task file. Updates ctx.task_id, ctx.task_text, resume fields."""
        request = ctx.request
        resume.resume_existing = request.task_path.exists()

        debug_log(
            "H2",
            "orc_core/task_execution.py:execute:task_state",
            "task file state",
            {"task_path": str(request.task_path), "exists": resume.resume_existing},
        )

        if not resume.resume_existing:
            return None

        try:
            active = json.loads(request.task_path.read_text(encoding="utf-8"))
            active_task_id = active.get("task_id")
            active_task_text = active.get("task_text")
            active_backlog_raw = str(active.get("backlog_path") or "").strip()
            raw_conversation_id = active.get("conversation_id", None)
            resume.resume_id = str(raw_conversation_id or "").strip() or None
            raw_restart_count = active.get("restart_count", 0)
            try:
                resume.persisted_restart_count = max(int(raw_restart_count), 0)
            except (TypeError, ValueError):
                resume.persisted_restart_count = 0
            resume.elapsed_before_start = read_task_active_seconds(request.task_path, expected_task_id=str(active_task_id or ""))
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
            log_event(self.log_path, "ERROR", "failed to read task file", error=str(exc))
            _logger.warning(
                f"⚠️ Не удалось прочитать {request.task_path}. "
                "Исправь/удали файл состояния или запусти с --drop для чистого старта."
            )
            ctx.ts_exec.result = "continue"
            ctx.ts_exec.reason = "task_file_read_failed"
            return TaskExecutionResult(status=TaskExecutionStatus.CONTINUE, reason="task_file_read_failed", delay_seconds=max(request.timing.poll, 0.2))

        same_backlog = True
        if active_backlog_raw:
            try:
                same_backlog = Path(active_backlog_raw).resolve() == request.backlog_path.resolve()
            except (OSError, ValueError):
                same_backlog = active_backlog_raw == str(request.backlog_path)

        if not same_backlog:
            log_event(
                self.log_path,
                "WARN",
                "resume state ignored: backlog mismatch",
                task_backlog=active_backlog_raw,
                expected_backlog=str(request.backlog_path),
            )
            resume.resume_existing = False
            resume.resume_id = None
            resume.persisted_restart_count = 0
            resume.elapsed_before_start = 0.0

        if resume.resume_existing and active_task_id and request.task_path.exists():
            from .task_source import MarkdownTaskSource

            if MarkdownTaskSource(ctx.base_backlog_path).is_task_done(active_task_id):
                log_event(self.log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
                _logger.info(f"✅ {active_task_id} уже отмечена [x]. Удаляю {request.task_path} и продолжаю.")
                try:
                    request.task_path.unlink()
                    delete_runtime_state_file(request.task_path, self.log_path, reason="stale_done_task_file")
                except OSError as exc:
                    log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                ctx.ts_exec.result = "continue"
                ctx.ts_exec.reason = "stale_done_task_file"
                return TaskExecutionResult(status=TaskExecutionStatus.CONTINUE, reason="stale_done_task_file")

        if resume.resume_existing:
            ctx.task_id = active_task_id or ctx.task_id
            ctx.task_text = active_task_text or ctx.task_text
            log_event(self.log_path, "INFO", "resume existing task", task_id=ctx.task_id)
            _logger.info(f"↩️ Обнаружена активная задача, запускаю resume для {ctx.task_id}.")
            if not resume.resume_id:
                log_event(
                    self.log_path,
                    "WARN",
                    "task file has no conversation_id — auto-dropping for fresh start",
                    task_id=ctx.task_id,
                    restart_count=resume.persisted_restart_count,
                )
                _logger.info(f"🗑️ Стейт {ctx.task_id} без conversation_id — авто-сброс для чистого старта.")
                try:
                    request.task_path.unlink()
                    delete_runtime_state_file(request.task_path, self.log_path, reason="auto_drop_no_conversation")
                except OSError:
                    pass
                resume.resume_existing = False
                resume.resume_id = None
                # Preserve restart_count so the agent knows it's a continuation
                resume.elapsed_before_start = 0.0
            log_event(
                self.log_path,
                "INFO",
                "resume selection",
                conversation_id=resume.resume_id or "",
                resume_from_latest=False,
                restart_count=resume.persisted_restart_count,
                active_seconds=resume.elapsed_before_start,
            )
        return None

    def _init_task_file(self, ctx: _ExecutionContext, resume: _ResumeState) -> None:
        """Create or enrich task file and persist session state."""
        request = ctx.request
        if not resume.resume_existing:
            write_task_file(
                request.base_workdir,
                request.task,
                request.backlog_path,
                self.log_path,
                restart_count=0,
                task_path_override=request.task_path,
            )
            if request.task_path.exists():
                try:
                    payload = json.loads(request.task_path.read_text(encoding="utf-8"))
                    if ctx.worktree_path_value:
                        payload["worktree_path"] = ctx.worktree_path_value
                    payload["branch_name"] = str(payload.get("branch_name") or "")
                    payload["status"] = "active"
                    write_json_atomic(request.task_path, payload, ensure_ascii=False, indent=2)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    log_event(self.log_path, "WARN", "failed to enrich task state with worktree metadata", error=str(exc))
            # Kanban session manager handles its own notifications
        if request.task_path.exists():
            try:
                session_payload = json.loads(request.task_path.read_text(encoding="utf-8"))
                save_active_session(
                    request.base_workdir,
                    {
                        "version": 1,
                        "task_id": str(session_payload.get("task_id") or ctx.task_id),
                        "session_id": str(session_payload.get("session_id") or ""),
                        "task_file": str(request.task_path),
                        "worktree_path": str(session_payload.get("worktree_path") or ctx.worktree_path_value),
                        "conversation_id": str(session_payload.get("conversation_id") or resume.resume_id or ""),
                        "status": "active",
                    },
                )
                session_id = str(session_payload.get("session_id") or "").strip()
                if session_id:
                    save_session_manifest(request.base_workdir, session_id, session_payload)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                log_event(self.log_path, "WARN", "failed to persist active session snapshot", error=str(exc))

    def _prepare_stages(self, ctx: _ExecutionContext) -> None:
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

    def _run_stage_loop(self, ctx: _ExecutionContext, resume: _ResumeState) -> TaskExecutionResult:
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
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    data={"restart_count": restart_count, "stage_id": stage_id, "stage_index": stage_index + 1},
                ) as ts_attempt:
                    update_task_restart_count(request.task_path, self.log_path, restart_count)
                    log_event(
                        self.log_path,
                        "INFO",
                        "launching agent",
                        task_id=task_id,
                        restart_count=restart_count,
                        stage_id=stage_id,
                        stage_index=stage_index + 1,
                        stage_total=len(stage_specs),
                    )
                    try:
                        active_monitor = self.worker.launch(
                            workdir=request.workdir,
                            prompt_path=prompt_path,
                            model=stage_model,
                            log_path=self.log_path,
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
                        )
                    except FileNotFoundError:
                        _logger.error("❌ agent не найден. Установите Cursor CLI (agent) и попробуйте снова.")
                        ts_attempt.result = "failed"
                        ts_attempt.reason = "agent_not_found"
                        ts_exec.result = "failed"
                        ts_exec.reason = "agent_not_found"
                        return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="agent_not_found")

                    try:
                        with timeline_step(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="wait_for_completion",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            attempt=attempt_number,
                        ) as ts_wait:
                            result = wait_for_completion(
                                task_path=request.task_path,
                                monitor=active_monitor,
                                poll=request.timing.poll,
                                stall_timeout=request.timing.stall_timeout,
                                task_ttl=request.timing.task_ttl,
                                elapsed_before_start=elapsed_before_start_stage,
                                ignore_initial_backlog_done=enforce_stage_artifacts and stage_index > 0,
                                log_path=self.log_path,
                                nudge_after=request.timing.nudge_after,
                                nudge_cooldown=request.timing.nudge_cooldown,
                                nudge_text=request.timing.nudge_text,
                                task_id=task_id,
                                task_text=task_text,
                                timeline_id=timeline_id,
                                attempt=attempt_number,
                                escape_requested=is_stop_requested,
                            )
                            ts_wait.result = result
                    finally:
                        try:
                            active_monitor.stop()
                        except Exception:
                            pass
                        _cleanup_monitor_processes(active_monitor, self.log_path, label="agent")

                    debug_log(
                        "H8",
                        "orc_core/task_execution.py:execute:completion_state",
                        "completion state",
                        {
                            "result": result,
                            "monitor_is_none": active_monitor is None,
                            "lines": active_monitor.metrics.total_lines,
                            "commands": active_monitor.metrics.command_count,
                            "tokens_total": active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-",
                            "stage_id": stage_id,
                        },
                    )

                    if result == TaskCompletionStatus.COMPLETED:
                        stage_failure, stage_next_index, stage_completed_final = self._complete_stage_impl(
                            ctx,
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
                            return self._finalize_completed_impl(ctx, task_id, task_text, tag, active_monitor)
                        break
                    if result == TaskCompletionStatus.MODEL_UNAVAILABLE:
                        log_event(
                            self.log_path,
                            "ERROR",
                            "agent model unavailable; stopping without restart",
                            task_id=task_id,
                            model=stage_model,
                        )
                        _logger.error(
                            "❌ Выбранная модель недоступна для `agent`. "
                            "Проверьте `agent --list-models` и укажите доступную модель через `--model`."
                        )
                        ts_attempt.result = "failed"
                        ts_attempt.reason = "model_unavailable"
                        ts_exec.result = "failed"
                        ts_exec.reason = "model_unavailable"
                        return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="model_unavailable")
                    if result == TaskCompletionStatus.WAITING_FOR_INPUT:
                        ts_attempt.result = "waiting_for_input"
                        restart_count += 1
                        update_task_restart_count(request.task_path, self.log_path, restart_count)
                        log_event(
                            self.log_path,
                            "INFO",
                            "waiting_for_input_budget_tick",
                            task_id=task_id,
                            restart_count=restart_count,
                            max_restarts=request.timing.max_restarts,
                        )
                        if restart_count > request.timing.max_restarts:
                            log_event(
                                self.log_path,
                                "ERROR",
                                "max restarts exceeded while waiting for input",
                                task_id=task_id,
                                restart_count=restart_count,
                                max_restarts=request.timing.max_restarts,
                            )
                            _logger.error("❌ Агент зациклился на запросе follow-up ввода. Лимит перезапусков исчерпан.")
                            ts_exec.result = "failed"
                            ts_exec.reason = "max_restarts_exceeded"
                            return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="max_restarts_exceeded")
                        delay = max(request.timing.nudge_cooldown, request.timing.poll, 1.0)
                        timeline_instant(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="restart_backoff_sleep",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            attempt=attempt_number,
                            result="continue",
                            reason="waiting_for_input",
                            data={"delay_seconds": delay},
                        )
                        _logger.warning(
                            f"[orc] агент запросил follow-up ввод; продолжу цикл через {delay:.1f}s "
                            "(resume сохранен, задача не потеряна)"
                        )
                        ts_exec.result = "continue"
                        ts_exec.reason = "waiting_for_input"
                        return TaskExecutionResult(status=TaskExecutionStatus.CONTINUE, reason="waiting_for_input", delay_seconds=delay)
                    # Backlog done detection for non-completed results
                    done_action, done_result, done_next_index, missing_artifact_retry_budget = self._check_backlog_done(
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
                    log_event(self.log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                    debug_log(
                        "H6",
                        "orc_core/task_execution.py:execute:max_restarts",
                        "max restarts exceeded",
                        {"task_id": task_id, "restart_count": restart_count, "max_restarts": request.timing.max_restarts},
                    )
                    _logger.error("❌ Агент не завершил задачу. Проверь логи.")
                    ts_exec.result = "failed"
                    ts_exec.reason = "max_restarts_exceeded"
                    return TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="max_restarts_exceeded")
                log_event(self.log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
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
                log_event(self.log_path, "INFO", "restart backoff", task_id=task_id, restart_count=restart_count, delay_seconds=delay)
                with timeline_step(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="restart_backoff_sleep",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
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

    def _check_backlog_done(
        self,
        ctx: _ExecutionContext,
        *,
        result: str,
        stage_id: str,
        stage_index: int,
        stage_is_final: bool,
        attempt_number: int,
        ts_attempt,
        tag: str,
        active_monitor,
        restart_count: int,
        missing_artifact_retry_budget: int,
    ) -> tuple[str, Optional[TaskExecutionResult], Optional[int], int]:
        """Check if task was marked done in backlog after non-completed monitor result.
        Returns (action, early_result, stage_next_index, updated_retry_budget).
        action: 'none' | 'return' | 'break'
        """
        request = ctx.request
        base_backlog_path = ctx.base_backlog_path
        runtime_backlog_path = ctx.runtime_backlog_path
        task_id = ctx.task_id
        task_text = ctx.task_text
        ts_exec = ctx.ts_exec

        # Kanban mode: _board sentinel is not a real backlog — skip done-detection
        if base_backlog_path.name == "_board" or base_backlog_path.is_dir():
            return "none", None, None, missing_artifact_retry_budget

        complete_kwargs = dict(
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

        try:
            from .task_source import MarkdownTaskSource

            base_done = MarkdownTaskSource(base_backlog_path).is_task_done(task_id)
            runtime_done = False
            if runtime_backlog_path != base_backlog_path:
                runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(task_id)

            if base_done:
                log_event(
                    self.log_path,
                    "WARN",
                    "task marked done after non-completed monitor result",
                    task_id=task_id,
                    monitor_result=result,
                )
                action, early_result, next_idx, missing_artifact_retry_budget = self._process_done_result(
                    ctx,
                    complete_kwargs=complete_kwargs,
                    completion_reason="base_backlog_marked_done",
                    monitor_result=result,
                    stage_id=stage_id,
                    missing_artifact_retry_budget=missing_artifact_retry_budget,
                    active_monitor=active_monitor,
                    restart_count=restart_count,
                    tag=tag,
                    retry_log_msg="task marked done but stage artifact missing after process exit; retrying",
                )
                if action in ("return", "break"):
                    return action, early_result, next_idx, missing_artifact_retry_budget

            if runtime_done:
                if _should_defer_base_backlog_sync_to_integration(
                    integrate_to_main=request.integrate_to_main,
                    base_backlog_path=base_backlog_path,
                    runtime_backlog_path=runtime_backlog_path,
                ):
                    log_event(
                        self.log_path,
                        "INFO",
                        "runtime backlog marked done; deferring base backlog sync until main integration",
                        task_id=task_id,
                        monitor_result=result,
                        base_backlog_path=str(base_backlog_path),
                        runtime_backlog_path=str(runtime_backlog_path),
                    )
                    debug_log(
                        "MI3",
                        "orc_core/task_execution.py:TaskExecutionEngine.execute",
                        "deferred base backlog sync because runtime backlog done will be carried by task commit",
                        {
                            "task_id": task_id,
                            "monitor_result": result,
                            "base_backlog_path": str(base_backlog_path),
                            "runtime_backlog_path": str(runtime_backlog_path),
                        },
                    )
                else:
                    synced = _sync_done_task_from_runtime_to_base(
                        task_id=task_id,
                        base_backlog_path=base_backlog_path,
                        runtime_backlog_path=runtime_backlog_path,
                        log_path=self.log_path,
                    )
                    if not synced:
                        log_event(
                            self.log_path,
                            "ERROR",
                            "runtime backlog marked done but base backlog sync failed",
                            task_id=task_id,
                            base_backlog_path=str(base_backlog_path),
                            runtime_backlog_path=str(runtime_backlog_path),
                        )
                        ts_exec.result = "failed"
                        ts_exec.reason = "runtime_backlog_sync_failed"
                        return "return", TaskExecutionResult(status=TaskExecutionStatus.FAILED, reason="runtime_backlog_sync_failed"), None, missing_artifact_retry_budget
                    log_event(
                        self.log_path,
                        "WARN",
                        "task marked done in runtime worktree backlog after non-completed monitor result",
                        task_id=task_id,
                        monitor_result=result,
                        base_backlog_path=str(base_backlog_path),
                        runtime_backlog_path=str(runtime_backlog_path),
                    )
                action, early_result, next_idx, missing_artifact_retry_budget = self._process_done_result(
                    ctx,
                    complete_kwargs=complete_kwargs,
                    completion_reason="runtime_backlog_marked_done",
                    monitor_result=result,
                    stage_id=stage_id,
                    missing_artifact_retry_budget=missing_artifact_retry_budget,
                    active_monitor=active_monitor,
                    restart_count=restart_count,
                    tag=tag,
                    retry_log_msg="runtime backlog marked done but stage artifact missing after process exit; retrying",
                )
                if action in ("return", "break"):
                    return action, early_result, next_idx, missing_artifact_retry_budget

        except Exception as exc:
            log_event(
                self.log_path,
                "ERROR",
                "failed to inspect backlog completion after non-completed monitor result",
                task_id=task_id,
                monitor_result=result,
                error=str(exc),
            )

        return "none", None, None, missing_artifact_retry_budget

    def _process_done_result(
        self,
        ctx: _ExecutionContext,
        *,
        complete_kwargs: dict,
        completion_reason: str,
        monitor_result: str,
        stage_id: str,
        missing_artifact_retry_budget: int,
        active_monitor,
        restart_count: int,
        tag: str,
        retry_log_msg: str,
    ) -> tuple[str, Optional[TaskExecutionResult], Optional[int], int]:
        """Process a done detection: validate stage, handle retry/finalize.
        Returns (action, result, stage_next_index, updated_retry_budget).
        action: 'return' | 'break' | 'retry'
        """
        request = ctx.request
        task_id = ctx.task_id
        task_text = ctx.task_text

        stage_failure, stage_next_index, stage_completed_final = self._complete_stage_impl(
            ctx, **complete_kwargs, completion_reason=completion_reason,
        )
        if stage_failure is not None:
            if _should_retry_after_missing_stage_artifact(
                stage_failure=stage_failure,
                monitor_result=monitor_result,
                current_stage_id=stage_id,
                retry_budget_left=missing_artifact_retry_budget,
            ):
                missing_artifact_retry_budget -= 1
                log_event(
                    self.log_path,
                    "WARN",
                    retry_log_msg,
                    task_id=task_id,
                    stage_id=stage_id,
                    monitor_result=monitor_result,
                    reason=stage_failure.reason,
                    retry_budget_left=missing_artifact_retry_budget,
                )
                return "retry", None, None, missing_artifact_retry_budget
            return "return", stage_failure, None, missing_artifact_retry_budget

        if stage_completed_final and request.task_path.exists():
            try:
                request.task_path.unlink()
                delete_runtime_state_file(request.task_path, self.log_path, reason=completion_reason)
            except OSError as exc:
                log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
        if stage_completed_final:
            ctx.restart_count = restart_count
            finalize_result = self._finalize_completed_impl(ctx, task_id, task_text, tag, active_monitor)
            return "return", finalize_result, None, missing_artifact_retry_budget
        return "break", None, stage_next_index, missing_artifact_retry_budget


    def _finalize_completed_impl(self, ctx: _ExecutionContext, current_task_id: str, current_task_text: str, current_tag: str, monitor) -> TaskExecutionResult:
        return _finalize_completed(self, ctx, current_task_id, current_task_text, current_tag, monitor)

    def _complete_stage_impl(
        self,
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
        return _complete_stage(
            self, ctx,
            current_task_id=current_task_id,
            current_task_text=current_task_text,
            current_tag=current_tag,
            current_monitor=current_monitor,
            current_stage_id=current_stage_id,
            current_stage_index=current_stage_index,
            current_stage_is_final=current_stage_is_final,
            current_attempt_number=current_attempt_number,
            current_ts_attempt=current_ts_attempt,
            completion_reason=completion_reason,
        )

    async def execute_async(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        return await asyncio.to_thread(self.execute, request)
