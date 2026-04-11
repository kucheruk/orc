#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build TaskExecutionRequest for kanban mode agents."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Callable, Optional

from .backend import Backend
from .state_paths import parallel_task_path
from .state_paths import run_root as state_run_root
from .monitor_types import MonitorSnapshot
from .task_execution_types import ModelConfig, TaskExecutionRequest, TemplateConfig, TimingConfig
from .task_source import Task


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
    args: Namespace,
    backend: Backend,
    commit_template: str,
    merge_expert_template: str,
    merge_expert_model: str,
    main_branch: str,
    progress: tuple[int, int, int],
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
) -> TaskExecutionRequest:
    task_path = parallel_task_path(base_workdir, session_id)
    task_path.parent.mkdir(parents=True, exist_ok=True)
    done, in_progress, total = progress
    model = str(getattr(args, "model", "") or backend.default_model())
    commit_model = str(getattr(args, "commit_model", "") or model)

    return TaskExecutionRequest(
        task=task,
        backlog_path=_ensure_board_sentinel(tasks_dir),
        backlog_arg=str(tasks_dir),
        task_path=task_path,
        workdir=workdir,
        base_workdir=base_workdir,
        run_root=state_run_root(base_workdir, f"kanban-{session_id}"),
        timing=TimingConfig(
            poll=float(getattr(args, "poll", 0.5)),
            stall_timeout=float(getattr(args, "stall_timeout", 300.0)),
            task_ttl=task_ttl,
            max_restarts=int(getattr(args, "max_restarts", 1)),
            report_interval=float(getattr(args, "report_interval", 30.0)),
            summary_lines=int(getattr(args, "summary_lines", 5)),
            nudge_after=int(getattr(args, "nudge_after", 0)),
            nudge_cooldown=float(getattr(args, "nudge_cooldown", 120.0)),
            nudge_text=str(getattr(args, "nudge_text", "")),
            commit_stall_timeout=float(getattr(args, "commit_stall_timeout", 120.0)),
            commit_ttl=float(getattr(args, "commit_ttl", 300.0)),
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
        allow_fallback_commits=False,
        enforce_stage_artifacts=False,
        stage_specs=(),
        progress_done=done,
        progress_total=total,
        progress_in_progress=in_progress,
        agent_env={"ORC_SESSION_ID": session_id, "ORC_BASE_WORKSPACE": base_workdir, "ORC_TASK_FILE": str(task_path), "PYTHONDONTWRITEBYTECODE": "1"},
        snapshot_publisher=snapshot_publisher,
    )

