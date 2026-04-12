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

from ..cli.orc_config import OrcConfig
from ..git.integration_manager import IntegrationManager
from .kanban_agent_output import process_agent_result
from ..board.kanban_constants import STAGE_DONE, STAGE_HANDOFF, Action
from ..tasks.task_execution_types import TaskExecutionStatus
from ..board.kanban_distributor import KanbanDistributor
from .kanban_protocols import CompletionNotifier, RunnerLifecycle, RunnerStateManager
from ..board.kanban_pull import WorkAssignment
from .kanban_publisher import KanbanPublisher
from .kanban_roles import build_prompt
from ..infra.logging import log_event
from ..infra.quit_signal import is_quit_after_task_requested
from .session_types import SessionSlot, SlotStatus
from ..tasks.task_execution import TaskExecutionEngine
from ..tasks.task_source import Task
from ..git.worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree

_logger = logging.getLogger(__name__)


class KanbanWorkerRunner:
    """Runs worker agent loops: pick task, execute, handle results."""

    _FAIL_BLOCK_THRESHOLD = 2  # consecutive failures before auto-blocking a card

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutionEngine,
        distributor: KanbanDistributor,
        publisher: KanbanPublisher,
        config: OrcConfig,
        main_branch: str,
        slots_lock: threading.Lock,
        worktree_lock: threading.Lock,
        card_fail_counts: dict[str, int],
        completed_tasks: list[str],
        failed_tasks: list[str],
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
        self._card_fail_counts = card_fail_counts
        self._completed_tasks = completed_tasks
        self._failed_tasks = failed_tasks
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
            slot.crash_traceback = traceback.format_exc()[:2000]
            slot.error = f"worker_crashed:{type(exc).__name__}"
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
                old_stage = card.stage
                old_action = card.action
                old_cos = card.class_of_service
                errors = process_agent_result(self._distributor.board, card, role)
                if not errors:
                    self._completed_tasks.append(card.id)
                    self._publisher.log_complete(card.id, role, elapsed)
                    self._notifier.notify_completion(card, role, old_stage, old_action, old_cos, elapsed)
                else:
                    self._publisher._emit("escalate", card.id,
                                           f"{card.id} validation failed: {'; '.join(errors[:3])}")
                    log_event(self._log_path, "WARN", "agent output validation failed",
                              task_id=card.id, role=role, errors=str(errors))
                    self._failed_tasks.append(card.id)
            else:
                reason = result.reason if result else "no result"
                self._publisher._emit("escalate", card.id, f"{card.id} {role} failed: {reason}")
                self._failed_tasks.append(card.id)
                self.increment_fail_and_maybe_block(card, f"agent returned: {reason}")
        except Exception as exc:
            self._publisher._emit("escalate", card.id,
                                   f"{card.id} ERROR: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "assignment failed",
                      task_id=card.id, error=str(exc))
            self._failed_tasks.append(card.id)
            self.increment_fail_and_maybe_block(card, f"{type(exc).__name__}: {exc}")
        else:
            # Reset failure counter on success
            if card.id in self._card_fail_counts:
                del self._card_fail_counts[card.id]
                self._state_manager.mark_dirty()
        finally:
            # Integrate worktree commits into main before cleanup
            if worktree and card.stage == STAGE_DONE:
                task_obj = slot.task or Task(task_id=card.id, text=card.title or card.id, done=True)
                integrated = self._integrator.integrate(slot, task_obj, worktree.worktree_path)
                if integrated:
                    with self._worktree_lock:
                        cleanup_task_worktree(worktree, self._log_path)
                else:
                    log_event(self._log_path, "WARN", "integration failed, keeping worktree",
                              task_id=card.id, worktree=worktree.worktree_path)
                    self._publisher._emit("escalate", card.id,
                                           f"{card.id} cherry-pick to {self._main_branch} failed; "
                                           f"card moved back to Handoff")
                    board = self._distributor.board
                    card.action = Action.INTEGRATING
                    board.move_card(card, STAGE_HANDOFF, allow_backward=True,
                                    reason="cherry-pick failed")
                    board.save_card(card)
            slot.task = None
            self._distributor.release_card(card.id)

    # ── Failure tracking ────────────────────────────────────────

    def increment_fail_and_maybe_block(self, card: KanbanCard, error_desc: str) -> None:
        """Track consecutive failures for a card. Block it after threshold."""
        count = self._card_fail_counts.get(card.id, 0) + 1
        self._card_fail_counts[card.id] = count
        self._state_manager.mark_dirty()
        if count >= self._FAIL_BLOCK_THRESHOLD:
            try:
                card.block(error_desc)
                self._distributor.board.save_card(card)
                self._publisher._emit("escalate", card.id,
                                       f"{card.id} marked Blocked after {count} consecutive failures: {error_desc}")
                log_event(self._log_path, "WARN", "card blocked after repeated failures",
                          task_id=card.id, fail_count=count, error=error_desc)
                self._notifier.send_telegram(
                    f"\U0001f6ab {card.id} \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u0430 \u043f\u043e\u0441\u043b\u0435 {count} \u043f\u043e\u0434\u0440\u044f\u0434 \u043e\u0448\u0438\u0431\u043e\u043a: {error_desc}",
                )
            except (OSError, ConnectionError, TimeoutError, ValueError):
                pass
