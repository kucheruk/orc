#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker runner: executes kanban card assignments in agent threads."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from ..config import OrcConfig
from ..supervision.outcomes import TaskOutcomeTracker
from ..git.integration_manager import IntegrationManager
from ..board.stage_constants import STAGE_DONE
from ..models.task_status import TaskExecutionStatus
from .kanban_protocols import CompletionNotifier, EventPublisher, RunnerLifecycle, RunnerStateManager, WorkDistributor
from ..board.kanban_pull import WorkAssignment
from .kanban_agent_output import process_agent_result
from .kanban_roles import build_prompt
from ..log import log_event
from ..quit_signal import is_quit_after_task_requested
from ..use_cases.process_task_result import (
    process_completed_task,
    handle_task_failure,
    escalate_if_threshold_reached,
)
from ..use_cases.finalize_task_worktree import finalize_completed_worktree
from ..models.session_types import SessionSlot, SlotStatus
from .kanban_protocols import TaskExecutor
from ..models.task_dto import Task
from ..models.git_dto import WorktreeSession
from ..git.worktree_flow import cleanup_task_worktree, create_task_worktree

_logger = logging.getLogger(__name__)


class KanbanWorkerRunner:
    """Runs worker agent loops: pick task, execute, handle results."""

    _FAIL_BLOCK_THRESHOLD = 2  # consecutive failures before auto-blocking a card

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutor,
        distributor: WorkDistributor,
        publisher: EventPublisher,
        config: OrcConfig,
        main_branch: str,
        slots_lock: threading.Lock,
        worktree_lock: threading.Lock,
        outcomes: TaskOutcomeTracker,
        lifecycle: RunnerLifecycle,
        notifier: CompletionNotifier,
        state_manager: RunnerStateManager,
        integrator: IntegrationManager,
    ) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._engine = engine
        self._distributor = distributor
        self._publisher = publisher
        self._config = config
        self._main_branch = main_branch
        self._slots_lock = slots_lock
        self._worktree_lock = worktree_lock
        self._outcomes = outcomes
        self._lifecycle = lifecycle
        self._notifier = notifier
        self._state_manager = state_manager
        self._integrator = integrator

    # ── Main loop ───────────────────────────────────────────────

    def run(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self._publisher._emit("system", "", f"{sid} worker started, scanning board...")
        try:
            idle_reason_logged: str = ""
            while self._lifecycle.should_continue(slot):
                self._distributor.refresh()
                assignment = self._distributor.pick_worker_task(sid)
                if assignment is None:
                    reason = self._distributor.diagnose_no_work()
                    if reason != idle_reason_logged:
                        self._publisher._emit("system", "", f"{sid} idle — {reason}")
                        idle_reason_logged = reason
                    self._lifecycle.sleep(2.0)
                    if not self._distributor.has_remaining_work():
                        self._publisher._emit("system", "", f"{sid} no remaining work, stopping")
                        break
                    continue
                idle_reason_logged = ""
                self.execute_assignment(slot, assignment)
                if is_quit_after_task_requested():
                    self._publisher._emit("system", "", f"{sid} finished task, exiting (quit-after-task)")
                    break
                self._lifecycle.sleep(1.0)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.mark_crashed(exc, traceback.format_exc())
            self._publisher._emit("escalate", "", f"{sid} CRASHED: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "worker crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    # ── Assignment execution ────────────────────────────────────

    def execute_assignment(self, slot: SessionSlot, assignment: WorkAssignment) -> None:
        card, role, sid = assignment.card, assignment.role, slot.session_id
        self._publisher.log_assign(card.id, role, sid)
        log_event(self._log_path, "INFO", "executing",
                  session_id=sid, task_id=card.id, role=role, stage=card.stage)
        prompt = build_prompt(role, card, self._distributor.board, main_branch=self._main_branch)
        task_start = time.time()
        worktree: Optional[WorktreeSession] = None
        try:
            if assignment.needs_worktree:
                with self._worktree_lock:
                    worktree = create_task_worktree(
                        base_workdir=self._workdir, task_id=card.id,
                        log_path=self._log_path, main_branch=self._main_branch,
                    )
                wd = worktree.worktree_path
                if not worktree.reused:
                    self._publisher._emit("system", card.id, f"{card.id} worktree ready")
            else:
                wd = self._workdir
            task = Task(task_id=card.id, text=card.title or card.id, done=False)
            slot.task = task
            self._publisher._emit("system", card.id, f"{card.id} launching {role} agent...")
            commit_phase = self._config.commit_phase and assignment.needs_worktree
            result = self._engine.execute(self._state_manager.make_request(task, prompt, wd, sid,
                                                              commit_phase, 1800.0))
            if result and result.status == TaskExecutionStatus.COMPLETED:
                elapsed = time.time() - task_start
                errors = process_completed_task(
                    board=self._distributor.board, card=card, role=role,
                    elapsed=elapsed, outcomes=self._outcomes,
                    publisher=self._publisher, notifier=self._notifier,
                    log_path=self._log_path,
                    agent_result_processor=process_agent_result,
                )
                if errors:
                    self._outcomes.record_failed(card.id)
            else:
                reason = result.reason if result else "no result"
                handle_task_failure(card, reason, self._outcomes, self._publisher, role)
                escalate_if_threshold_reached(
                    card, f"agent returned: {reason}",
                    self._distributor.board, self._outcomes,
                    self._publisher, self._notifier, self._log_path,
                )
        except Exception as exc:
            self._publisher._emit("escalate", card.id,
                                   f"{card.id} ERROR: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "assignment failed",
                      task_id=card.id, error=str(exc))
            self._outcomes.record_failed(card.id)
            escalate_if_threshold_reached(
                card, f"{type(exc).__name__}: {exc}",
                self._distributor.board, self._outcomes,
                self._publisher, self._notifier, self._log_path,
            )
        else:
            # Reset failure counter on success
            self._outcomes.reset_fail_count(card.id)
        finally:
            # Integrate worktree commits into main before cleanup
            if worktree and card.stage == STAGE_DONE:
                finalize_completed_worktree(
                    card=card, worktree=worktree, slot=slot,
                    board=self._distributor.board, integrator=self._integrator,
                    cleanup_fn=cleanup_task_worktree, log_path=self._log_path,
                    main_branch=self._main_branch, publisher=self._publisher,
                    worktree_lock=self._worktree_lock,
                )
            slot.task = None
            self._distributor.release_card(card.id)
