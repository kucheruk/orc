#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import time
from argparse import Namespace
from pathlib import Path
from typing import Callable, Optional, Tuple

from .hooks import ensure_repo_hooks, ensure_repo_hooks_config
from .logging import log_event
from .quit_signal import is_quit_after_task_requested
from .session_state import clear_active_session, save_active_session, save_worktree_record
from .state_paths import metrics_path, run_root as state_run_root, stats_path
from .stream_monitor_state import MonitorSnapshot
from .task_state import delete_runtime_state_file, runtime_state_path
from .task_execution import TaskExecutionEngine, TaskExecutionRequest, TaskStageSpec
from .task_source import MarkdownTaskSource, Task
from .ui import ui_error, ui_info
from .worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree


TaskSourceFactory = Callable[[Path], MarkdownTaskSource]


class BacklogOrchestrator:
    def __init__(
        self,
        *,
        workdir: str,
        backlog_path: Path,
        args: Namespace,
        task_path: Path,
        run_root: Path,
        log_path: Path,
        prompt_template: str,
        continue_template: str,
        commit_template: str,
        merge_expert_template: str = "",
        engine: TaskExecutionEngine,
        merge_expert_model: str = "",
        stage_specs: Optional[list[TaskStageSpec]] = None,
        integrate_to_main: bool = True,
        main_branch: str = "main",
        use_task_worktrees: bool = True,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        task_source_factory: TaskSourceFactory = MarkdownTaskSource,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.workdir = workdir
        self.backlog_path = backlog_path
        self.args = args
        self.task_path = task_path
        self.run_root = run_root
        self.log_path = log_path
        self.prompt_template = prompt_template
        self.continue_template = continue_template
        self.commit_template = commit_template
        self.merge_expert_template = merge_expert_template
        self.engine = engine
        self.merge_expert_model = (merge_expert_model or "").strip()
        self.stage_specs = tuple(stage_specs or ())
        self.integrate_to_main = bool(integrate_to_main)
        self.main_branch = (main_branch or "main").strip() or "main"
        self.use_task_worktrees = bool(use_task_worktrees)
        self.snapshot_publisher = snapshot_publisher
        self.task_source_factory = task_source_factory
        self.sleep_fn = sleep_fn
        self.last_failure_reason = ""

    def _restore_worktree_from_state(self, open_task: Task) -> Optional[WorktreeSession]:
        if not self.task_path.exists():
            return None
        try:
            payload = json.loads(self.task_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if str(payload.get("task_id") or "").strip() != open_task.task_id:
            return None
        worktree_path = str(payload.get("worktree_path") or "").strip()
        branch_name = str(payload.get("branch_name") or "").strip()
        if not worktree_path:
            return None
        if not Path(worktree_path).exists():
            return None
        return WorktreeSession(
            base_workdir=self.workdir,
            worktree_path=worktree_path,
            branch_name=branch_name,
            task_id=open_task.task_id,
        )

    def run(self) -> int:
        mode = str(getattr(self.args, "mode", "backlog") or "backlog").strip().lower()
        selected_task_id = str(getattr(self.args, "task_id", "") or "").strip()
        single_mode = mode == "single"
        drop_pending = bool(self.args.drop)
        drop_override: Optional[Tuple[str, str]] = None
        active_worktree: Optional[WorktreeSession] = None

        while True:
            self._ensure_hooks()
            task_source = self.task_source_factory(self.backlog_path)
            tasks = task_source.list_tasks()
            total = len(tasks)
            done = sum(1 for t in tasks if t.done)
            open_task = task_source.get_first_open_task()
            if single_mode:
                if not selected_task_id:
                    ui_error("Single mode requires task id.")
                    return 2
                selected_task = task_source.get_task_by_id(selected_task_id)
                if not selected_task:
                    ui_error(f"❌ Задача не найдена в backlog: {selected_task_id}")
                    return 2
                if selected_task.done:
                    ui_info(f"✅ {selected_task_id} уже отмечена [x]. Выход.")
                    return 0
                open_task = selected_task

            if drop_pending and self.task_path.exists():
                drop_pending = False
                started_flag = False
                try:
                    active = json.loads(self.task_path.read_text(encoding="utf-8"))
                    active_task_id = (active.get("task_id") or "").strip()
                    active_task_text = (active.get("task_text") or "").strip()
                    conversation_id = str(active.get("conversation_id") or "").strip()
                    started_flag = bool(active.get("start_notified") or conversation_id)
                    if active_task_id:
                        drop_override = (active_task_id, active_task_text or active_task_id)
                except Exception as exc:
                    log_event(self.log_path, "ERROR", "drop: failed to read task file (still deleting)", error=str(exc))
                try:
                    self.task_path.unlink()
                    delete_runtime_state_file(self.task_path, self.log_path, reason="drop_active_task_state")
                    log_event(
                        self.log_path,
                        "WARN",
                        "drop: active task state deleted",
                        task_path=str(self.task_path),
                        started=started_flag,
                    )
                except Exception as exc:
                    log_event(self.log_path, "ERROR", "drop: failed to delete task file", error=str(exc))
                    return 2
                if drop_override:
                    dropped_task_id, _ = drop_override
                    if dropped_task_id:
                        dropped_task = next((t for t in tasks if t.task_id == dropped_task_id), None)
                        if dropped_task and not dropped_task.done:
                            open_task = dropped_task
                        else:
                            drop_override = None

            if not open_task:
                log_event(self.log_path, "INFO", "backlog complete")
                ui_info("✅ BACKLOG.md: невыполненных пунктов не осталось. Выход.")
                return 0

            short = (open_task.text[:120] + "…") if len(open_task.text) > 120 else open_task.text
            ui_info(f"▶️ Текущая задача: {open_task.task_id} — {short}")
            if self.use_task_worktrees and active_worktree is None:
                active_worktree = self._restore_worktree_from_state(open_task)
                if active_worktree is not None:
                    ui_info(f"[orc] worktree restored: {active_worktree.worktree_path}")
            if self.use_task_worktrees and (active_worktree is None or active_worktree.task_id != open_task.task_id):
                try:
                    active_worktree = create_task_worktree(
                        base_workdir=self.workdir,
                        task_id=open_task.task_id,
                        log_path=self.log_path,
                        main_branch=self.main_branch,
                    )
                    save_worktree_record(
                        self.workdir,
                        open_task.task_id,
                        {
                            "version": 1,
                            "task_id": open_task.task_id,
                            "worktree_path": active_worktree.worktree_path,
                            "branch_name": str(getattr(active_worktree, "branch_name", "") or ""),
                            "base_workdir": self.workdir,
                        },
                    )
                    ui_info(f"[orc] worktree: {active_worktree.worktree_path}")
                except Exception as exc:
                    self.last_failure_reason = f"worktree_create_failed:{type(exc).__name__}"
                    log_event(
                        self.log_path,
                        "ERROR",
                        "task worktree creation failed",
                        reason=self.last_failure_reason,
                        task_id=open_task.task_id,
                        error=str(exc),
                    )
                    ui_error(f"❌ Не удалось создать worktree для {open_task.task_id}: {exc}")
                    return 1

            execution_workdir = active_worktree.worktree_path if active_worktree is not None else self.workdir
            self._ensure_hooks_for_workspace(execution_workdir)
            try:
                use_sdlc_pipeline = bool(self.stage_specs)
                result = self.engine.execute(
                    TaskExecutionRequest(
                        task=open_task,
                        backlog_path=self.backlog_path,
                        backlog_arg=self.args.backlog,
                        task_path=self.task_path,
                        workdir=execution_workdir,
                        base_workdir=self.workdir,
                        run_root=state_run_root(self.workdir, "backlog-run"),
                        model=self.args.model,
                        commit_model=(self.args.commit_model or "").strip() or self.args.model,
                        merge_expert_model=self.merge_expert_model or ((self.args.commit_model or "").strip() or self.args.model),
                        prompt_template=self.prompt_template,
                        continue_template=self.continue_template,
                        commit_template=self.commit_template,
                        merge_expert_template=self.merge_expert_template,
                        commit_phase=bool(self.args.commit_phase) and not use_sdlc_pipeline,
                        integrate_to_main=self.integrate_to_main,
                        main_branch=self.main_branch,
                        allow_fallback_commits=bool(getattr(self.args, "allow_fallback_commits", False)),
                        poll=self.args.poll,
                        stall_timeout=self.args.stall_timeout,
                        task_ttl=self.args.task_ttl,
                        max_restarts=self.args.max_restarts,
                        report_interval=self.args.report_interval,
                        summary_lines=self.args.summary_lines,
                        nudge_after=self.args.nudge_after,
                        nudge_cooldown=self.args.nudge_cooldown,
                        nudge_text=self.args.nudge_text,
                        commit_stall_timeout=self.args.commit_stall_timeout,
                        commit_ttl=self.args.commit_ttl,
                        progress_done=done,
                        progress_total=total,
                        enforce_stage_artifacts=bool(getattr(self.args, "require_stage_artifacts", False)),
                        stage_specs=self.stage_specs,
                        agent_output_log_path=str(getattr(self.args, "agent_output_log_path", "") or "").strip() or None,
                        agent_env={
                            "ORC_TASK_FILE": str(self.task_path),
                            "ORC_TASK_RUNTIME_FILE": str(runtime_state_path(self.task_path)),
                            "ORC_BASE_WORKSPACE": str(Path(self.workdir)),
                            "ORC_STATS_FILE": str(stats_path(self.workdir)),
                            "ORC_METRICS_FILE": str(metrics_path(self.workdir)),
                        },
                        snapshot_publisher=self.snapshot_publisher,
                    )
                )
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self.last_failure_reason = f"unexpected_engine_exception:{type(exc).__name__}"
                log_event(
                    self.log_path,
                    "ERROR",
                    "task execution crashed unexpectedly",
                    reason=self.last_failure_reason,
                    task_id=open_task.task_id,
                    error=str(exc),
                )
                ui_error(f"❌ Задача упала из-за внутренней ошибки ORC: {self.last_failure_reason}")
                return 1

            if result.status == "failed":
                self.last_failure_reason = result.reason or "execution_failed"
                log_event(self.log_path, "ERROR", "task execution failed", reason=self.last_failure_reason, task_id=open_task.task_id)
                ui_error(f"❌ Задача завершилась с ошибкой: {self.last_failure_reason}")
                if self.use_task_worktrees and active_worktree is not None:
                    ui_info(f"[orc] worktree preserved for diagnostics: {active_worktree.worktree_path}")
                save_active_session(
                    self.workdir,
                    {
                        "version": 1,
                        "task_id": open_task.task_id,
                        "task_file": str(self.task_path),
                        "worktree_path": active_worktree.worktree_path if active_worktree is not None else "",
                        "status": "failed",
                        "reason": self.last_failure_reason,
                    },
                )
                return 1
            if result.delay_seconds > 0:
                self.sleep_fn(result.delay_seconds)
            if result.status == "completed":
                if self.use_task_worktrees and active_worktree is not None:
                    try:
                        cleanup_task_worktree(active_worktree, self.log_path)
                    except Exception as exc:
                        self.last_failure_reason = f"worktree_cleanup_failed:{type(exc).__name__}"
                        log_event(
                            self.log_path,
                            "ERROR",
                            "task worktree cleanup failed",
                            reason=self.last_failure_reason,
                            task_id=open_task.task_id,
                            worktree_path=active_worktree.worktree_path,
                            error=str(exc),
                        )
                        ui_error(
                            f"❌ Задача завершена, но cleanup worktree не удался: {active_worktree.worktree_path}. "
                            "Worktree сохранён для диагностики."
                        )
                        return 1
                    active_worktree = None
                clear_active_session(self.workdir)
                if is_quit_after_task_requested():
                    if result.committed:
                        ui_info("[orc] graceful quit requested: current task completed and committed. Exiting.")
                        return 0
                    ui_info("[orc] graceful quit requested, but commit phase is not completed yet; continuing.")
                if single_mode:
                    ui_info("✅ Single task mode: задача выполнена. Выход.")
                    return 0
                ui_info("[orc] pause 5s before next task (Ctrl+C to stop)")
                self.sleep_fn(5)

    def _ensure_hooks(self) -> None:
        before_path, stop_path = ensure_repo_hooks(self.workdir)
        hooks_path = ensure_repo_hooks_config(self.workdir, before_path, stop_path, self.log_path)
        log_event(self.log_path, "INFO", "hooks ready", hooks_config=str(hooks_path))

    def _ensure_hooks_for_workspace(self, workdir: str) -> None:
        target = str(workdir or "").strip()
        if not target or target == self.workdir:
            return
        before_path, stop_path = ensure_repo_hooks(target)
        hooks_path = ensure_repo_hooks_config(target, before_path, stop_path, self.log_path)
        log_event(self.log_path, "INFO", "worktree hooks ready", hooks_config=str(hooks_path), workdir=target)

    async def run_async(self) -> int:
        return await asyncio.to_thread(self.run)
