#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker runner: executes kanban card assignments in agent threads."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from ...git.integration_manager import IntegrationManager
from ...log import log_event
from ...quit_signal import is_quit_after_task_requested
from ...tasks.completion.outcomes import TaskOutcomeTracker
from ...tasks.ports import GitIntegrationPort
from ..infra.protocols import CompletionNotifier, EventPublisher, RunnerLifecycle, RunnerStateManager, TaskExecutor, WorkDistributor
from ..roles import build_prompt
from ..session.types import SessionSlot, SlotStatus
from .worker_assignment import WorkerAssignmentExecutor

_logger = logging.getLogger(__name__)


class KanbanWorkerRunner:
    """Runs worker agent loops: pick task, execute, handle results."""

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutor,
        distributor: WorkDistributor,
        publisher: EventPublisher,
        config,
        main_branch: str,
        slots_lock,
        worktree_lock,
        outcomes: TaskOutcomeTracker,
        lifecycle: RunnerLifecycle,
        notifier: CompletionNotifier,
        state_manager: RunnerStateManager,
        integrator: IntegrationManager,
        git_integration: GitIntegrationPort,
    ) -> None:
        self._publisher = publisher
        self._distributor = distributor
        self._lifecycle = lifecycle
        self._slots_lock = slots_lock
        self._outcomes = outcomes
        self._executor = WorkerAssignmentExecutor(
            workdir=workdir,
            log_path=log_path,
            engine=engine,
            distributor=distributor,
            publisher=publisher,
            config=config,
            main_branch=main_branch,
            worktree_lock=worktree_lock,
            outcomes=outcomes,
            notifier=notifier,
            state_manager=state_manager,
            integrator=integrator,
            git_integration=git_integration,
        )
        self._log_path = log_path

    def run(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self._publisher.emit("system", "", f"{sid} worker started, scanning board...")
        try:
            idle_reason_logged = ""
            while self._lifecycle.should_continue(slot):
                self._distributor.refresh()
                assignment = self._distributor.pick_worker_task(sid)
                if assignment is None:
                    reason = self._distributor.diagnose_no_work()
                    if reason != idle_reason_logged:
                        self._publisher.emit("system", "", f"{sid} idle — {reason}")
                        idle_reason_logged = reason
                    self._lifecycle.sleep(2.0)
                    if not self._distributor.has_remaining_work():
                        self._publisher.emit("system", "", f"{sid} no remaining work, stopping")
                        break
                    continue
                idle_reason_logged = ""
                self.execute_assignment(slot, assignment)
                if is_quit_after_task_requested():
                    self._publisher.emit("system", "", f"{sid} finished task, exiting (quit-after-task)")
                    break
                self._lifecycle.sleep(1.0)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.mark_crashed(exc, traceback.format_exc())
            self._publisher.emit("escalate", "", f"{sid} CRASHED: {type(exc).__name__}: {exc}")
            log_event(
                self._log_path,
                "ERROR",
                "worker crashed",
                session_id=sid,
                error=str(exc),
                traceback=traceback.format_exc()[:2000],
            )
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    def execute_assignment(self, slot: SessionSlot, assignment) -> None:
        self._executor.execute(slot, assignment, prompt_builder=build_prompt)
