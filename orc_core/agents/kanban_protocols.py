#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared Protocol interfaces for kanban runner communication (ISP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from ..board.kanban_card import KanbanCard
    from ..infra.session_types import SessionSlot
    from ..tasks.task_execution_types import TaskExecutionRequest
    from ..infra.task_types import Task


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
