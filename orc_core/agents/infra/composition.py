#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composition factory for KanbanSessionManager — single place where the dependency graph is wired."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

from ...board.fs_card_repository import FsCardRepository
from ...board.kanban_board import KanbanBoard
from ...board.kanban_distributor import KanbanDistributor
from ...config import OrcConfig
from ...git.conflict_resolver import ConflictResolver
from ...git.integration_manager import IntegrationManager
from ...git.safe_files import SafeFilesGuard
from ...git.subprocess_git import SubprocessGitRunner
from ...git.task_adapters import SubprocessGitIntegration
from ...git.branch_resolver import DEFAULT_MAIN_BRANCH, detect_base_branch
from ...incident.manager import IncidentManager
from ...backends.backend import Backend
from ...infra.io.state_paths_adapter import FsStatePaths
from ...infra.io.task_state_adapter import FsTaskStateWriter
from ...infra.process.lifecycle import SubprocessProcessLifecycle
from ...tasks.execution.engine import TaskExecutionEngine
from .adapters import (
    DirectiveAdapter,
    LifecycleAdapter,
    NotifierAdapter,
    SessionControllerAdapter,
    StateManagerAdapter,
)
from .board_event_bridge import BoardEventBridge
from .directive_queue import DirectiveQueue
from .notification_service import NotificationService
from .publisher import KanbanPublisher
from .request_factory import KanbanRequestFactory
from ..session.manager import KanbanSessionManager
from ..session.state_persistence import load_kanban_state
from ..runners.teamlead import KanbanTeamleadRunner
from ..runners.worker import KanbanWorkerRunner
from ..session.pool import SessionPool
from ...tasks.completion.outcomes import TaskOutcomeTracker


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
    main_branch: str = DEFAULT_MAIN_BRANCH,
    max_sessions: int = 4,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> KanbanSessionManager:
    """Construct a KanbanSessionManager with all production collaborators wired.

    This is the single composition root — the whole dependency graph is visible
    here. KanbanSessionManager.__init__ accepts only fully-constructed deps,
    including its worker/teamlead runners.
    """
    resolved_main_branch = (main_branch or "").strip() or detect_base_branch(workdir)
    merge_expert_model_resolved = (merge_expert_model or "").strip()
    worktree_lock = threading.Lock()
    process_lifecycle = SubprocessProcessLifecycle()
    state_writer = FsTaskStateWriter()
    state_paths = FsStatePaths()
    git_integration = SubprocessGitIntegration()

    # Base infrastructure
    board = KanbanBoard(tasks_dir, repo=FsCardRepository())
    distributor = KanbanDistributor(board)
    git_runner = SubprocessGitRunner()
    safe_files = SafeFilesGuard(workdir, frozenset(), log_path=log_path)
    conflicts = ConflictResolver(workdir)
    integrator = IntegrationManager(
        workdir=workdir,
        main_branch=resolved_main_branch,
        log_path=log_path,
        safe_tracked_paths=frozenset(),
        git=git_runner,
        conflicts=conflicts,
        safe_files=safe_files,
    )
    publisher = KanbanPublisher()

    card_fail_counts, arbitrated_at_loop, applied_result_runs = load_kanban_state(workdir)
    outcomes = TaskOutcomeTracker(
        card_fail_counts=card_fail_counts,
        arbitrated_at_loop=arbitrated_at_loop,
        applied_result_runs=applied_result_runs,
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

    # Cross-cutting services used by runners
    board_events = BoardEventBridge(
        workdir=workdir,
        distributor=distributor,
        publisher=publisher,
        outcomes=outcomes,
        pool=pool,
    )
    request_factory = KanbanRequestFactory(
        workdir=workdir,
        tasks_dir=tasks_dir,
        config=config,
        backend=backend,
        distributor=distributor,
        pool=pool,
        commit_template=commit_template,
        merge_expert_template=merge_expert_template,
        merge_expert_model=merge_expert_model_resolved,
        main_branch=resolved_main_branch,
        process_lifecycle=process_lifecycle,
        state_writer=state_writer,
        state_paths=state_paths,
        git_integration=git_integration,
    )

    # Protocol adapters (no back-reference to session manager)
    lifecycle_adapter = LifecycleAdapter(pool)
    notifier_adapter = NotifierAdapter(notifications)
    directive_adapter = DirectiveAdapter(directives)
    state_adapter = StateManagerAdapter(request_factory, outcomes)

    # Worker runner — needs state_adapter but not session_controller_adapter
    worker_runner = KanbanWorkerRunner(
        workdir=workdir,
        log_path=log_path,
        engine=engine,
        distributor=distributor,
        publisher=publisher,
        config=config,
        main_branch=resolved_main_branch,
        slots_lock=pool.slots_lock,
        worktree_lock=worktree_lock,
        outcomes=outcomes,
        lifecycle=lifecycle_adapter,
        notifier=notifier_adapter,
        state_manager=state_adapter,
        integrator=integrator,
        git_integration=git_integration,
    )

    # Session controller depends on worker runner as thread target
    session_ctrl_adapter = SessionControllerAdapter(pool, worker_runner.run)

    incident_mgr = IncidentManager(
        distributor=distributor,
        publisher=publisher,
        engine=engine,
        slots=pool.slots,
        slots_lock=pool.slots_lock,
        outcomes=outcomes,
        log_path=log_path,
        workdir=workdir,
        max_sessions=pool.max_sessions,
        sleep_fn=sleep_fn,
        state_manager=state_adapter,
        session_controller=session_ctrl_adapter,
    )
    teamlead_runner = KanbanTeamleadRunner(
        workdir=workdir,
        log_path=log_path,
        engine=engine,
        distributor=distributor,
        publisher=publisher,
        incident_mgr=incident_mgr,
        slots_lock=pool.slots_lock,
        outcomes=outcomes,
        lifecycle=lifecycle_adapter,
        notifier=notifier_adapter,
        state_manager=state_adapter,
        state_paths=state_paths,
        directives=directive_adapter,
        git_integration=git_integration,
        active_tasks_provider=pool.active_tasks_by_session,
        known_sessions_provider=pool.known_session_ids,
    )

    return KanbanSessionManager(
        workdir=workdir,
        tasks_dir=tasks_dir,
        config=config,
        log_path=log_path,
        distributor=distributor,
        integrator=integrator,
        publisher=publisher,
        pool=pool,
        outcomes=outcomes,
        directives=directives,
        notifications=notifications,
        board_events=board_events,
        request_factory=request_factory,
        worker_runner=worker_runner,
        teamlead_runner=teamlead_runner,
        process_lifecycle=process_lifecycle,
        main_branch=resolved_main_branch,
        sleep_fn=sleep_fn,
    )


def build_orchestrator(
    *,
    args,
    workdir: str,
    log_path: Path,
    backend: Backend,
    base_branch: str,
    commit_template: str = "",
    merge_expert_template: str = "",
    merge_expert_model: str = "",
) -> KanbanSessionManager:
    """Top-level composition root.

    Builds the TaskExecutionEngine, initializes the kanban board on disk,
    and assembles the full KanbanSessionManager graph. CLI and TUI entry
    points call this single function instead of wiring the engine
    themselves.
    """
    from ...board.kanban_init import init_kanban_board
    from ...notifications.adapters import TelegramNotify
    from ...tasks.execution.worker import AgentTaskWorker

    engine = TaskExecutionEngine(
        worker=AgentTaskWorker(backend=backend),
        log_path=log_path,
        notify=TelegramNotify(log_path=log_path),
    )
    tasks_dir = init_kanban_board(Path(workdir))
    orc_config = OrcConfig.from_namespace(args)
    return build_session_manager(
        workdir=workdir,
        tasks_dir=tasks_dir,
        config=orc_config,
        log_path=log_path,
        engine=engine,
        backend=backend,
        commit_template=commit_template,
        merge_expert_template=merge_expert_template,
        merge_expert_model=merge_expert_model,
        main_branch=base_branch,
        max_sessions=max(2, min(int(getattr(args, "max_sessions", 0) or 4), 4)),
    )
