#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task execution request/result/launch bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional

from ...tasks.ports import MonitorSnapshot
from ..dto import Task
from .config import ModelConfig, TemplateConfig, TimingConfig
from .stage import TaskStageSpec


@dataclass(frozen=True)
class TaskExecutionRequest:
    task: Task
    backlog_path: Path
    backlog_arg: str
    task_path: Path
    workdir: str
    base_workdir: str
    run_root: Path
    timing: TimingConfig
    models: ModelConfig
    templates: TemplateConfig
    commit_phase: bool
    integrate_to_main: bool
    main_branch: str
    allow_fallback_commits: bool
    progress_done: int
    progress_total: int
    progress_in_progress: int = 0
    enforce_stage_artifacts: bool = False
    stage_specs: tuple[TaskStageSpec, ...] = ()
    agent_output_log_path: Optional[str] = None
    agent_env: Optional[Mapping[str, str]] = None
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None


@dataclass(frozen=True)
class TaskExecutionResult:
    status: str
    reason: str = ""
    delay_seconds: float = 0.0
    committed: bool = False


@dataclass(frozen=True)
class LaunchConfig:
    """All parameters needed to launch an agent subprocess."""
    workdir: str
    prompt_path: Path
    model: str
    log_path: Path
    report_interval: float
    summary_lines: int
    task_id: str
    progress_done: int
    progress_total: int
    progress_in_progress: int = 0
    agent_output_log_path: Optional[str] = None
    agent_env: Optional[Mapping[str, str]] = None
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None
    resume_id: Optional[str] = None
    resume_latest: bool = False
    resume_prompt: Optional[str] = None
    timeline_id: str = ""
    attempt: int = 0
    backlog_task_lister: Optional[Callable] = None
    git_diff_fn: Optional[Callable] = None
