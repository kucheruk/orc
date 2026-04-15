#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from ...log import log_event
from ...observability import timeline_step
from ..backlog_query import MarkdownBacklogQuery
from ..completion.ports import BacklogQueryPort, NoopNotify, NotifyPort
from ..task_state import runtime_state_path
from .helpers import _build_agent_output_log_path, _resolve_runtime_backlog_path
from .preflight import preflight_integration
from .request import LaunchConfig, TaskExecutionRequest, TaskExecutionResult
from .resume import init_task_file, recover_resume_state
from .runtime import _ExecutionContext, _ResumeState
from .stage_loop import prepare_stages, run_stage_loop
from .worker import TaskWorker


__all__ = ["TaskExecutionEngine", "LaunchConfig", "TaskExecutionRequest", "TaskExecutionResult", "TaskWorker"]


class TaskExecutionEngine:
    def __init__(
        self,
        *,
        worker: TaskWorker,
        log_path: Path,
        notify: Optional[NotifyPort] = None,
        backlog_query: Optional[BacklogQueryPort] = None,
    ) -> None:
        self.worker = worker
        self.log_path = log_path
        self.notify: NotifyPort = notify or NoopNotify()
        self.backlog_query: BacklogQueryPort = backlog_query or MarkdownBacklogQuery()

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
        prepare_stages(ctx)
        return run_stage_loop(self, ctx, resume)

    async def execute_async(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        return await asyncio.to_thread(self.execute, request)
