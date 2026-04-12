#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data classes, protocols, and constants for task execution."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Protocol

if TYPE_CHECKING:
    from ..infra.backend import Backend as BackendProtocol


class TaskExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CONTINUE = "continue"


class TaskCompletionStatus(StrEnum):
    COMPLETED = "completed"
    STALLED = "stalled"
    TTL_EXCEEDED = "ttl_exceeded"
    PROCESS_EXITED = "process_exited"
    WAITING_FOR_INPUT = "waiting_for_input"
    MODEL_UNAVAILABLE = "model_unavailable"
from ..infra.runner import launch_agent_stream_json
from ..infra.monitor_types import MonitorSnapshot
from ..infra.task_types import Task


SDLC_FEEDBACK_MAX_ITERATIONS = 3

ETA_WINDOW_SIZE = 20


@dataclass(frozen=True)
class TaskStageSpec:
    stage_id: str
    model: str
    prompt_template: str


@dataclass(frozen=True)
class TimingConfig:
    poll: float
    stall_timeout: float
    task_ttl: float
    max_restarts: int
    report_interval: float
    summary_lines: int
    nudge_after: int
    nudge_cooldown: float
    nudge_text: str
    commit_stall_timeout: float
    commit_ttl: float


@dataclass(frozen=True)
class ModelConfig:
    model: str
    commit_model: str
    merge_expert_model: str


@dataclass(frozen=True)
class TemplateConfig:
    prompt_template: str
    continue_template: str
    commit_template: str
    merge_expert_template: str


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


class TaskWorker(Protocol):
    def launch(self, config: LaunchConfig): ...


class AgentTaskWorker:
    def __init__(self, backend: "BackendProtocol") -> None:
        self._backend = backend

    def launch(self, config: LaunchConfig):
        return launch_agent_stream_json(
            config.workdir,
            config.prompt_path,
            config.model,
            config.log_path,
            report_interval=config.report_interval,
            summary_lines=config.summary_lines,
            task_id=config.task_id,
            progress_done=config.progress_done,
            progress_total=config.progress_total,
            progress_in_progress=config.progress_in_progress,
            agent_output_log_path=config.agent_output_log_path,
            agent_env=config.agent_env,
            snapshot_publisher=config.snapshot_publisher,
            resume_id=config.resume_id,
            resume_latest=config.resume_latest,
            resume_prompt=config.resume_prompt,
            timeline_id=config.timeline_id,
            attempt=config.attempt,
            backend=self._backend,
        )


RESTART_REASON_TEXT = {
    TaskCompletionStatus.STALLED: "Ты перестал выдавать результат (завис). Переоцени свой подход.",
    TaskCompletionStatus.TTL_EXCEEDED: "Ты превысил лимит времени. Сделай коммит текущего прогресса или выбери более простой путь.",
    TaskCompletionStatus.PROCESS_EXITED: "Твой процесс неожиданно завершился (возможно, ошибка синтаксиса в bash).",
}


@dataclass(frozen=True)
class AgentPhaseSpec:
    """Describes how to run a sub-phase (commit, merge expert, etc.)."""
    step_name: str
    label: str
    model: str
    template: str
    workdir: str
    tag_suffix: str
    task_id_suffix: str
    stall_timeout: float
    ttl: float
