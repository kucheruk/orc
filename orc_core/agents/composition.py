#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composition factory for KanbanSessionManager — single place where the dependency graph is wired."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ..board.kanban_distributor import KanbanDistributor
from ..config import OrcConfig
from ..git.integration_manager import IntegrationManager
from ..infra.backend import Backend
from ..tasks.task_execution import TaskExecutionEngine
from .kanban_directive_queue import DirectiveQueue
from .kanban_notification_service import NotificationService
from .kanban_publisher import KanbanPublisher
from .kanban_session_manager import KanbanSessionManager
from .kanban_state_persistence import load_kanban_state
from .session_pool import SessionPool
from ..supervision.outcomes import TaskOutcomeTracker


def build_session_manager(
    *,
    workdir: str,
    tasks_dir: Path,
    config: OrcConfig,
    log_path: Path,
    engine: TaskExecutionEngine,
    backend: Backend,
    commit_template: str = "",
    merge_expert_template: str = "",
    merge_expert_model: str = "",
    main_branch: str = "main",
    max_sessions: int = 4,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> KanbanSessionManager:
    """Construct a KanbanSessionManager with all production collaborators wired.

    This is the single composition root — the whole dependency graph is visible
    here. KanbanSessionManager.__init__ accepts only fully-constructed deps.
    """
    resolved_main_branch = (main_branch or "main").strip() or "main"

    distributor = KanbanDistributor(tasks_dir)
    integrator = IntegrationManager(
        workdir=workdir,
        main_branch=resolved_main_branch,
        log_path=log_path,
        safe_tracked_paths=frozenset(),
    )
    publisher = KanbanPublisher()

    card_fail_counts, arbitrated_at_loop = load_kanban_state(workdir)
    outcomes = TaskOutcomeTracker(
        card_fail_counts=card_fail_counts,
        arbitrated_at_loop=arbitrated_at_loop,
    )

    directives = DirectiveQueue()
    notifications = NotificationService(
        workdir=workdir,
        log_path=log_path,
        get_progress=distributor.get_progress,
    )

    pool = SessionPool(
        max_sessions=max_sessions,
        publisher=publisher,
        log_path=log_path,
        sleep_fn=sleep_fn,
    )

    return KanbanSessionManager(
        workdir=workdir,
        tasks_dir=tasks_dir,
        config=config,
        log_path=log_path,
        engine=engine,
        backend=backend,
        distributor=distributor,
        integrator=integrator,
        publisher=publisher,
        pool=pool,
        outcomes=outcomes,
        directives=directives,
        notifications=notifications,
        commit_template=commit_template,
        merge_expert_template=merge_expert_template,
        merge_expert_model=merge_expert_model,
        main_branch=resolved_main_branch,
        sleep_fn=sleep_fn,
    )
