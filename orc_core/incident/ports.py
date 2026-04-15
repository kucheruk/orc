#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports for the incident subsystem — structural types it depends on.

These protocols are defined here (and not imported from agents/) so that
the incident package has no back-edge to agents, satisfying ADP. The
agents package supplies concrete implementations that structurally match
these shapes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from ..models.task_types import Task
    from ..tasks.execution.request import TaskExecutionRequest, TaskExecutionResult


class FailedTasksSource(Protocol):
    """Read-only source of failed task ids.

    IncidentManager queries this to decide whether an injected fix is itself
    failing. Any object exposing a ``failed_tasks`` list satisfies the port.
    """

    @property
    def failed_tasks(self) -> list[str]: ...


class IncidentStateManager(Protocol):
    """Builds task execution requests for triage tasks."""

    def mark_dirty(self) -> None: ...
    def make_request(
        self,
        task: "Task",
        prompt: str,
        workdir: str,
        session_id: str,
        commit_phase: bool,
        ttl: float,
    ) -> "TaskExecutionRequest": ...


class IncidentSessionController(Protocol):
    """Controls the session pool during incident scaling."""

    def add_session(self) -> Optional[str]: ...
    def remove_session(self, session_id: str) -> None: ...


class IncidentTaskExecutor(Protocol):
    """Runs a task (used to spawn the triage agent)."""

    log_path: Path

    def execute(self, request: "TaskExecutionRequest") -> "TaskExecutionResult": ...


class IncidentPublisher(Protocol):
    """Emits incident lifecycle events to the TUI / journal."""

    def log_incident(self, incident_id: str, message: str) -> None: ...
