#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared Protocol interfaces for kanban runner communication (ISP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol

from pathlib import Path

if TYPE_CHECKING:
    from ..board.kanban_board import KanbanBoard
    from ..board.kanban_card import KanbanCard
    from ..board.kanban_pull import WorkAssignment
    from ..models.session_types import SessionSlot
    from ..tasks.execution.request import TaskExecutionRequest, TaskExecutionResult
    from ..models.task_dto import Task


class RunnerLifecycle(Protocol):
    """Controls runner thread lifecycle (shared by worker and teamlead)."""

    def should_continue(self, slot: SessionSlot) -> bool: ...
    def sleep(self, seconds: float) -> None: ...


class RunnerStateManager(Protocol):
    """Manages state persistence and request building (shared by worker and teamlead)."""

    def mark_dirty(self) -> None: ...
    def make_request(
        self,
        task: Task,
        prompt: str,
        workdir: str,
        session_id: str,
        commit_phase: bool,
        ttl: float,
    ) -> TaskExecutionRequest: ...


class RunnerNotifier(Protocol):
    """Sends telegram notifications (shared base)."""

    def send_telegram(self, message: str) -> None: ...


class CompletionNotifier(Protocol):
    """Extended notifier with task completion support (worker-only)."""

    def send_telegram(self, message: str) -> None: ...
    def notify_completion(
        self,
        card: KanbanCard,
        role: str,
        old_stage: str,
        old_action: str,
        old_cos: str,
        elapsed: float,
    ) -> None: ...


class DirectiveSource(Protocol):
    """Provides user directives for the teamlead."""

    def pop_directive(self) -> Optional[str]: ...


class SessionController(Protocol):
    """Controls session pool (for incident management)."""

    def add_session(self) -> Optional[str]: ...
    def remove_session(self, session_id: str) -> None: ...


class TaskExecutor(Protocol):
    """Port for task execution — agents depend on this, not on the concrete engine."""

    log_path: Path

    def execute(self, request: "TaskExecutionRequest") -> "TaskExecutionResult": ...


class WorkDistributor(Protocol):
    """Port for kanban work distribution — runners depend on this, not on KanbanDistributor."""

    @property
    def board(self) -> "KanbanBoard": ...
    def refresh(self) -> None: ...
    def pick_worker_task(self, worker_id: str) -> Optional["WorkAssignment"]: ...
    def pick_teamlead_task(self, agent_id: str) -> Optional["KanbanCard"]: ...
    def diagnose_no_work(self) -> str: ...
    def has_remaining_work(self) -> bool: ...
    def release_card(self, card_id: str) -> None: ...
    def needs_escalation(self, card: "KanbanCard") -> bool: ...
    def get_progress(self) -> tuple[int, int, int]: ...


class EventPublisher(Protocol):
    """Port for publishing kanban events to TUI — runners depend on this, not on KanbanPublisher."""

    def _emit(self, category: str, card_id: str, message: str) -> None: ...
    def log_assign(self, card_id: str, role: str, agent_id: str) -> None: ...
    def log_complete(self, card_id: str, role: str, elapsed_seconds: float) -> None: ...
    def log_escalate(self, card_id: str, message: str) -> None: ...
    def log_incident(self, incident_id: str, message: str) -> None: ...
    def log_arbitration(self, card_id: str, decision: str) -> None: ...
    def log_move(self, card_id: str, from_stage: str, to_stage: str, reason: str = "") -> None: ...
    def log_unblock(self, card_id: str, directive: str) -> None: ...
    def log_action_change(self, card_id: str, old_action: str, new_action: str, role: str) -> None: ...
