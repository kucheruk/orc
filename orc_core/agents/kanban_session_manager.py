#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban-mode session manager: teamlead + workers with pull-based role dispatch."""

from __future__ import annotations

import asyncio
import signal
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from ..infra.backend import Backend
from ..git.integration_manager import IntegrationManager
from ..incident.manager import IncidentManager
from ..board.kanban_distributor import KanbanDistributor
from ..board.stage_constants import STAGE_INBOX, STAGE_SHORT_NAMES
from ..config import OrcConfig
from .kanban_adapters import (
    DirectiveAdapter,
    LifecycleAdapter,
    NotifierAdapter,
    SessionControllerAdapter,
    StateManagerAdapter,
)
from .kanban_directive_queue import DirectiveQueue
from .kanban_notification_service import NotificationService
from .kanban_publisher import KanbanPublisher
from .kanban_request_builder import build_kanban_request
from .kanban_state_persistence import (
    cleanup_done_worktrees,
    release_stale_agents,
    save_kanban_state,
)
from .kanban_teamlead_runner import KanbanTeamleadRunner
from .kanban_worker_runner import KanbanWorkerRunner
from ..git.project_hooks import fire_hooks
from ..board.kanban_role_registry import ROLE_TEAMLEAD
from ..use_cases.create_card import create_inbox_card
from ..use_cases.unblock_card import unblock_card as unblock_card_uc
from ..log import log_event
from ..quit_signal import is_quit_after_task_requested, is_stop_requested
from .session_pool import SessionPool
from .task_outcome_tracker import TaskOutcomeTracker
from ..models.session_types import (
    MANAGER_POLL_SECONDS,
    STAGGER_DELAY_SECONDS,
    SessionSlot,
)
from ..infra.monitoring.monitor_types import MonitorSnapshot
from ..tasks.task_execution import TaskExecutionEngine
from ..infra.process.process_groups import kill_own_process_group

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130


class KanbanSessionManager:
    """Orchestrates AI agents on a kanban board using a pull system."""

    def __init__(
        self,
        *,
        workdir: str,
        tasks_dir: Path,
        config: OrcConfig,
        log_path: Path,
        engine: TaskExecutionEngine,
        backend: Backend,
        distributor: KanbanDistributor,
        integrator: IntegrationManager,
        publisher: KanbanPublisher,
        pool: SessionPool,
        outcomes: TaskOutcomeTracker,
        directives: DirectiveQueue,
        notifications: NotificationService,
        commit_template: str = "",
        merge_expert_template: str = "",
        merge_expert_model: str = "",
        main_branch: str = "main",
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.backend = backend
        self.workdir = workdir
        self.tasks_dir = tasks_dir
        self.config = config
        self.log_path = log_path
        self.engine = engine
        self.commit_template = commit_template
        self.merge_expert_template = merge_expert_template
        self.merge_expert_model = (merge_expert_model or "").strip()
        self.main_branch = (main_branch or "main").strip() or "main"
        self.sleep_fn = sleep_fn

        self._distributor = distributor
        self._integrator = integrator
        self._worktree_lock = threading.Lock()

        self.publisher = publisher
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._outcomes = outcomes
        self._directives = directives
        self._notifications = notifications
        self._pool = pool

        self._wire_runners()

    def _wire_runners(self) -> None:
        """Build protocol adapters and wire up runners with all dependencies."""
        self._lifecycle_adapter = LifecycleAdapter(self._pool)
        self._notifier_adapter = NotifierAdapter(self._notifications)
        self._state_adapter = StateManagerAdapter(self)
        self._directive_adapter = DirectiveAdapter(self._directives)
        self._session_ctrl_adapter = SessionControllerAdapter(self)

        self._incident_mgr = IncidentManager(
            distributor=self._distributor,
            publisher=self.publisher,
            engine=self.engine,
            slots=self._pool.slots,
            slots_lock=self._pool.slots_lock,
            outcomes=self._outcomes,
            log_path=self.log_path,
            workdir=self.workdir,
            max_sessions=self._pool.max_sessions,
            sleep_fn=self.sleep_fn,
            state_manager=self._state_adapter,
            session_controller=self._session_ctrl_adapter,
        )
        self._worker_runner = KanbanWorkerRunner(
            workdir=self.workdir,
            log_path=self.log_path,
            engine=self.engine,
            distributor=self._distributor,
            publisher=self.publisher,
            config=self.config,
            main_branch=self.main_branch,
            slots_lock=self._pool.slots_lock,
            worktree_lock=self._worktree_lock,
            outcomes=self._outcomes,
            lifecycle=self._lifecycle_adapter,
            notifier=self._notifier_adapter,
            state_manager=self._state_adapter,
            integrator=self._integrator,
        )
        self._teamlead_runner = KanbanTeamleadRunner(
            workdir=self.workdir,
            log_path=self.log_path,
            engine=self.engine,
            distributor=self._distributor,
            publisher=self.publisher,
            incident_mgr=self._incident_mgr,
            slots_lock=self._pool.slots_lock,
            outcomes=self._outcomes,
            lifecycle=self._lifecycle_adapter,
            notifier=self._notifier_adapter,
            state_manager=self._state_adapter,
            directives=self._directive_adapter,
        )

    # ── Public API ──────────────────────────────────────────────

    def request_add_session(self) -> Optional[str]:
        return self._pool.request_add(target=self._run_worker)

    def request_remove_session(self, session_id: str = "") -> None:
        self._pool.request_remove(session_id)

    def run(self, snapshot_publisher) -> int:
        self._pool.snapshot_publisher = snapshot_publisher
        self._started_at = time.time()
        self.publisher.set_started_at(self._started_at)
        self._wire_board_callbacks()
        self._distributor.refresh()

        # Cleanup stale state from previous runs
        done_ids = release_stale_agents(self._distributor.board, self.publisher)
        cleanup_done_worktrees(done_ids, self.workdir, self.log_path, self.publisher)

        done, _ip, total = self._distributor.get_progress()
        self.publisher._emit("system", "", f"Kanban started: {total} cards, {self._pool.max_sessions} agents")
        self._publish_board_state()
        self._integrator.recover_stale_git_state()

        self._pool.start_session(role=ROLE_TEAMLEAD, target=self._run_teamlead)
        self._publish_board_state()
        self.sleep_fn(STAGGER_DELAY_SECONDS)
        for _ in range(self._pool.max_sessions - 1):
            if is_stop_requested():
                break
            self._pool.start_session(role="worker", target=self._run_worker)
            self.sleep_fn(STAGGER_DELAY_SECONDS)
        try:
            return _manager_loop(
                pool=self._pool,
                distributor=self._distributor,
                publisher=self.publisher,
                publish_board=self._publish_board_state,
                run_worker=self._run_worker,
                sleep_fn=self.sleep_fn,
            )
        except KeyboardInterrupt:
            raise
        finally:
            _shutdown_all(self._pool)

    async def run_async(self, snapshot_publisher) -> int:
        return await asyncio.to_thread(self.run, snapshot_publisher)

    def shutdown(self) -> None:
        _shutdown_all(self._pool)

    def get_summary(self) -> str:
        elapsed = time.time() - self._started_at if self._started_at > 0 else 0
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
        done, _ip, total = self._distributor.get_progress()
        completed = self._outcomes.completed_tasks
        failed = self._outcomes.failed_tasks
        lines = [f"Completed: {len(completed)} tasks in {time_str}"]
        if completed:
            lines.append(f"  Tasks: {', '.join(completed)}")
        if failed:
            lines.append(f"  Failed: {', '.join(failed)}")
        lines.append(f"  Board: {done}/{total} done")
        return "\n".join(lines)

    def add_inbox_card(self, text: str) -> None:
        board = self._distributor.board
        def _log_created(cid, title):
            log_event(self.log_path, "INFO", "inbox card created", card_id=cid, title=title)
        card = create_inbox_card(board, text, on_created=_log_created)
        self.publisher.log_inbox(card.id, text)

    def unblock_card(self, card_id: str, directive: str) -> None:
        board = self._distributor.board
        def _log_unblocked(cid, dir_text):
            log_event(self.log_path, "INFO", "card unblocked", card_id=cid, directive=dir_text)
        if unblock_card_uc(board, card_id, directive, on_unblocked=_log_unblocked):
            self.publisher.log_unblock(card_id, directive)

    def queue_teamlead_directive(self, text: str) -> None:
        self._directives.push(text)
        self.publisher._emit("directive", "", f"Directive queued for teamlead: {text}")
        log_event(self.log_path, "INFO", "teamlead directive queued", directive=text[:200])

    # ── Board callbacks ─────────────────────────────────────────

    def _wire_board_callbacks(self) -> None:
        board = self._distributor.board

        def _on_move(cid: str, frm: str, to: str, reason: str) -> None:
            self.publisher.log_move(cid, frm, to, reason)
            card = board.card_by_id(cid)
            fire_hooks(self.workdir, "on_move", {
                "ORC_CARD_ID": cid,
                "ORC_CARD_TITLE": card.title if card else "",
                "ORC_FROM_STAGE": STAGE_SHORT_NAMES.get(frm, frm),
                "ORC_TO_STAGE": STAGE_SHORT_NAMES.get(to, to),
                "ORC_REASON": reason,
            })

        board.on_move(_on_move)
        board.on_action_change(lambda cid, old, new, role: self.publisher.log_action_change(cid, old, new, role))

    # ── State persistence ───────────────────────────────────────

    def mark_state_dirty(self) -> None:
        self._outcomes.mark_dirty()

    def _publish_board_state(self) -> None:
        self._distributor.refresh()
        self.publisher.publish_board(self._distributor.board, self._pool.session_snapshots)
        if self._outcomes.is_dirty():
            snapshot = self._outcomes.state_snapshot()
            save_kanban_state(self.workdir, snapshot["card_fail_counts"], snapshot["arbitrated_at_loop"])
            self._outcomes.clear_dirty()

    # ── Worker/teamlead thread targets ──────────────────────────

    def _run_worker(self, slot: SessionSlot) -> None:
        self._worker_runner.run(slot)

    def _run_teamlead(self, slot: SessionSlot) -> None:
        self._teamlead_runner.run(slot)

    # ── Helpers ──────────────────────────────────────────────────

    def _pop_directive(self) -> Optional[str]:
        return self._directives.pop()

    def _send_telegram(self, message: str) -> None:
        self._notifications.send_telegram(message)

    def _notify_completion(self, card, role, old_stage, old_action, old_cos, elapsed) -> None:
        self._notifications.notify_completion(card, role, old_stage, old_action, old_cos, elapsed)

    def make_request(self, task, prompt, workdir, session_id, commit_phase, task_ttl):
        def _pub(snapshot: MonitorSnapshot) -> None:
            self._pool.publish_snapshot(session_id, snapshot)
        return build_kanban_request(
            task=task, prompt=prompt, workdir=workdir, base_workdir=self.workdir,
            tasks_dir=self.tasks_dir, session_id=session_id, commit_phase=commit_phase,
            task_ttl=task_ttl, config=self.config, backend=self.backend,
            commit_template=self.commit_template, merge_expert_template=self.merge_expert_template,
            merge_expert_model=self.merge_expert_model, main_branch=self.main_branch,
            progress=self._distributor.get_progress(), snapshot_publisher=_pub,
        )

    def _board_diag_short(self) -> str:
        board = self._distributor.board
        inbox = board.cards_in_stage(STAGE_INBOX)
        free_inbox = sum(1 for c in inbox if not c.assigned_agent)
        total_assigned = sum(1 for c in board.cards if c.assigned_agent)
        return f"inbox={len(inbox)} (free={free_inbox}), assigned_total={total_assigned}"



# ── Standalone orchestration functions ──────────────────────────


def _manager_loop(
    *,
    pool: SessionPool,
    distributor: KanbanDistributor,
    publisher: KanbanPublisher,
    publish_board: Callable[[], None],
    run_worker: Callable,
    sleep_fn: Callable[[float], None],
) -> int:
    """Main event loop: reap finished sessions, check exit conditions, restart idle workers."""
    quit_after_logged = False
    quit_after_last_status = 0.0
    while True:
        pool.reap_finished()
        publish_board()
        if is_stop_requested():
            return EXIT_INTERRUPT
        if is_quit_after_task_requested():
            if not quit_after_logged:
                publisher._emit("system", "", "Quit-after-task: waiting for active agents to finish...")
                quit_after_logged = True
            running = pool.running_info()
            now = time.time()
            if running:
                if now - quit_after_last_status >= 10.0:
                    publisher._emit("system", "", f"Still working: {running}")
                    quit_after_last_status = now
            else:
                publisher._emit("system", "", "All agents finished, exiting")
                return EXIT_OK
        elif not pool.has_active():
            if distributor.has_remaining_work():
                pool.restart_idle(target=run_worker)
                if pool.has_active():
                    continue
            return EXIT_OK
        sleep_fn(MANAGER_POLL_SECONDS)


def _shutdown_all(pool: SessionPool) -> None:
    """Shutdown all session threads and kill child processes."""
    pool.shutdown_threads()
    for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT", "SIGINT"):
        sig = getattr(signal, sig_name, None)
        if sig:
            try:
                signal.signal(sig, signal.SIG_IGN)
            except Exception:
                pass
    kill_own_process_group()
