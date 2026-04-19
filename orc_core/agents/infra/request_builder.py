#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build TaskExecutionRequest for kanban mode agents."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Optional

from ...config import OrcConfig
from ...backends.backend import Backend
from ...infra.io.state_paths import parallel_task_path
from ...infra.io.state_paths import run_root as state_run_root
from ...contracts.session import MonitorSnapshot
from ...tasks.ports import GitIntegrationPort, ProcessLifecyclePort, StatePathsPort, TaskStateWriter
from ...tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from ...tasks.execution.request import TaskExecutionRequest
from ...tasks.dto import Task


def _ensure_board_sentinel(tasks_dir: Path) -> Path:
    """Create a minimal sentinel file so task_execution doesn't crash on backlog_path reads."""
    sentinel = tasks_dir / "_board"
    if not sentinel.exists():
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("# Kanban board sentinel — not a real backlog\n", encoding="utf-8")
    return sentinel


def build_kanban_request(
    *,
    task: Task,
    prompt: str,
    workdir: str,
    base_workdir: str,
    tasks_dir: Path,
    session_id: str,
    commit_phase: bool,
    task_ttl: float,
    config: OrcConfig,
    backend: Backend,
    commit_template: str,
    merge_expert_template: str,
    merge_expert_model: str,
    main_branch: str,
    progress: tuple[int, int, int],
    process_lifecycle: ProcessLifecyclePort,
    state_writer: TaskStateWriter,
    state_paths: StatePathsPort,
    git_integration: GitIntegrationPort,
    agent_env: Mapping[str, str] | None = None,
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
) -> TaskExecutionRequest:
    task_path = parallel_task_path(base_workdir, session_id)
    task_path.parent.mkdir(parents=True, exist_ok=True)
    done, in_progress, total = progress
    model = config.model or backend.default_model()
    commit_model = config.commit_model or model

    merged_agent_env = {
        "ORC_SESSION_ID": session_id,
        "ORC_BASE_WORKSPACE": base_workdir,
        "ORC_TASK_FILE": str(task_path),
        "PYTHONDONTWRITEBYTECODE": "1",
        **dict(agent_env or {}),
    }

    return TaskExecutionRequest(
        task=task,
        backlog_path=_ensure_board_sentinel(tasks_dir),
        backlog_arg=str(tasks_dir),
        task_path=task_path,
        workdir=workdir,
        base_workdir=base_workdir,
        run_root=state_run_root(base_workdir, f"kanban-{session_id}"),
        timing=TimingConfig(
            poll=config.poll,
            stall_timeout=config.stall_timeout,
            task_ttl=task_ttl,
            max_restarts=config.max_restarts,
            report_interval=config.report_interval,
            summary_lines=config.summary_lines,
            nudge_after=config.nudge_after,
            nudge_cooldown=config.nudge_cooldown,
            nudge_text=config.nudge_text,
            commit_stall_timeout=config.commit_stall_timeout,
            commit_ttl=config.commit_ttl,
        ),
        models=ModelConfig(
            model=model,
            commit_model=commit_model,
            merge_expert_model=merge_expert_model or commit_model,
        ),
        templates=TemplateConfig(
            prompt_template=prompt,
            continue_template="",
            commit_template=commit_template,
            merge_expert_template=merge_expert_template,
        ),
        commit_phase=commit_phase,
        integrate_to_main=False,
        main_branch=main_branch,
        allow_fallback_commits=True,
        enforce_stage_artifacts=False,
        stage_specs=(),
        progress_done=done,
        progress_total=total,
        progress_in_progress=in_progress,
        agent_env=merged_agent_env,
        snapshot_publisher=snapshot_publisher,
        process_lifecycle=process_lifecycle,
        state_writer=state_writer,
        state_paths=state_paths,
        git_integration=git_integration,
    )
