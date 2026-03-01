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
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine, TaskExecutionRequest
from .task_source import MarkdownTaskSource, Task
from .ui import ui_error, ui_info


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
        engine: TaskExecutionEngine,
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
        self.engine = engine
        self.snapshot_publisher = snapshot_publisher
        self.task_source_factory = task_source_factory
        self.sleep_fn = sleep_fn
        self.last_failure_reason = ""

    def run(self) -> int:
        mode = str(getattr(self.args, "mode", "backlog") or "backlog").strip().lower()
        selected_task_id = str(getattr(self.args, "task_id", "") or "").strip()
        single_mode = mode == "single"
        drop_pending = bool(self.args.drop)
        drop_override: Optional[Tuple[str, str]] = None

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

            try:
                result = self.engine.execute(
                    TaskExecutionRequest(
                        task=open_task,
                        backlog_path=self.backlog_path,
                        backlog_arg=self.args.backlog,
                        task_path=self.task_path,
                        workdir=self.workdir,
                        run_root=self.run_root,
                        model=self.args.model,
                        commit_model=(self.args.commit_model or "").strip() or self.args.model,
                        prompt_template=self.prompt_template,
                        continue_template=self.continue_template,
                        commit_template=self.commit_template,
                        commit_phase=bool(self.args.commit_phase),
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
                        agent_output_log_path=str(getattr(self.args, "agent_output_log_path", "") or "").strip() or None,
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
                return 1
            if result.delay_seconds > 0:
                self.sleep_fn(result.delay_seconds)
            if result.status == "completed":
                if single_mode:
                    ui_info("✅ Single task mode: задача выполнена. Выход.")
                    return 0
                ui_info("[orc] pause 5s before next task (Ctrl+C to stop)")
                self.sleep_fn(5)

    def _ensure_hooks(self) -> None:
        before_path, stop_path = ensure_repo_hooks(self.workdir)
        hooks_path = ensure_repo_hooks_config(self.workdir, before_path, stop_path, self.log_path)
        log_event(self.log_path, "INFO", "hooks ready", hooks_config=str(hooks_path))

    async def run_async(self) -> int:
        return await asyncio.to_thread(self.run)
