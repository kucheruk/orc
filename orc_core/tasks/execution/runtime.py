#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mutable runtime state for a single task execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .request import TaskExecutionRequest


@dataclass
class _ExecutionContext:
    """Mutable shared state passed between extracted methods of _execute_inner."""
    request: TaskExecutionRequest
    task_id: str
    task_text: str
    timeline_id: str
    ts_exec: object  # timeline step context manager
    effective_agent_output_log_path: str
    base_backlog_path: Path
    runtime_backlog_path: Path
    effective_agent_env: dict = field(default_factory=dict)
    worktree_path_value: str = ""
    restart_count: int = 0
    last_agent_result_file: str = ""
    last_agent_run_id: str = ""
    stage_specs: list = field(default_factory=list)
    artifact_bundle: object = None
    enforce_stage_artifacts: bool = False
    implementation_stage_index: Optional[int] = None
    feedback_iteration_count: int = 0


@dataclass
class _ResumeState:
    """Resume state recovered from existing task file."""
    resume_existing: bool = False
    resume_id: Optional[str] = None
    persisted_restart_count: int = 0
    elapsed_before_start: float = 0.0
