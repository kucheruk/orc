#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task worker port + agent-subprocess adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ...infra.runner import launch_agent_stream_json
from .request import LaunchConfig

if TYPE_CHECKING:
    from ...infra.backend import Backend as BackendProtocol


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
            backlog_task_lister=config.backlog_task_lister,
            git_diff_fn=config.git_diff_fn,
        )
