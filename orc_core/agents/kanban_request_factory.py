#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constructs TaskExecutionRequest objects for kanban worker/teamlead runs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..board.kanban_distributor import KanbanDistributor
from ..config import OrcConfig
from ..backends.backend import Backend
from ..infra.monitoring.monitor_dto import MonitorSnapshot
from .kanban_request_builder import build_kanban_request

if TYPE_CHECKING:
    from .session_pool import SessionPool


class KanbanRequestFactory:
    """Builds a TaskExecutionRequest using the current session context."""

    def __init__(
        self,
        *,
        workdir: str,
        tasks_dir: Path,
        config: OrcConfig,
        backend: Backend,
        distributor: KanbanDistributor,
        pool: "SessionPool",
        commit_template: str,
        merge_expert_template: str,
        merge_expert_model: str,
        main_branch: str,
    ) -> None:
        self._workdir = workdir
        self._tasks_dir = tasks_dir
        self._config = config
        self._backend = backend
        self._distributor = distributor
        self._pool = pool
        self._commit_template = commit_template
        self._merge_expert_template = merge_expert_template
        self._merge_expert_model = merge_expert_model
        self._main_branch = main_branch

    def make(self, task, prompt: str, workdir: str, session_id: str, commit_phase: bool, task_ttl: float):
        def _pub(snapshot: MonitorSnapshot) -> None:
            self._pool.publish_snapshot(session_id, snapshot)
        return build_kanban_request(
            task=task,
            prompt=prompt,
            workdir=workdir,
            base_workdir=self._workdir,
            tasks_dir=self._tasks_dir,
            session_id=session_id,
            commit_phase=commit_phase,
            task_ttl=task_ttl,
            config=self._config,
            backend=self._backend,
            commit_template=self._commit_template,
            merge_expert_template=self._merge_expert_template,
            merge_expert_model=self._merge_expert_model,
            main_branch=self._main_branch,
            progress=self._distributor.get_progress(),
            snapshot_publisher=_pub,
        )
