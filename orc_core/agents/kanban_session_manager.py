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

from ..infra.backend import Backend, get_backend
from ..git.integration_manager import IntegrationManager
from .kanban_incident_manager import IncidentManager
from ..board.kanban_distributor import KanbanDistributor
from ..board.kanban_constants import (
    STAGE_INBOX,
    STAGE_SHORT_NAMES,
)
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
    load_kanban_state,
    release_stale_agents,
    save_kanban_state,
)
from .kanban_teamlead_runner import KanbanTeamleadRunner
from .kanban_worker_runner import KanbanWorkerRunner
from ..git.project_hooks import fire_hooks
from ..board.kanban_role_registry import ROLE_TEAMLEAD
from ..use_cases.create_card import create_inbox_card
from ..use_cases.unblock_card import unblock_card as unblock_card_uc
from ..infra.io.logging import log_event
from ..infra.state.quit_signal import is_quit_after_task_requested, is_stop_requested
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
        commit_template: str = "",
        merge_expert_template: str = "",
        merge_expert_model: str = "",
        main_branch: str = "main",
        max_sessions: int = 4,
        backend: Backend | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        # ── Injectable dependencies (None = create defaults) ───
        distributor: Optional[KanbanDistributor] = None,
        integrator: Optional[IntegrationManager] = None,
        publisher: Optional[KanbanPublisher] = None,
        pool: Optional[SessionPool] = None,
    ) -> None:
        self.backend: Backend = backend or get_backend()
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

        self._distributor = distributor or KanbanDistributor(tasks_dir)
        self._integrator = integrator or IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
            safe_tracked_paths=frozenset(),
        )
        self._worktree_lock = threading.Lock()

        self.publisher = publisher or KanbanPublisher()
        self.last_failure_reason = ""
        self._started_at = 0.0
        card_fail_counts, arbitrated_at_loop = load_kanban_state(workdir)
        self._outcomes = TaskOutcomeTracker(
            card_fail_counts=card_fail_counts,
            arbitrated_at_loop=arbitrated_at_loop,
        )
        self._directives = DirectiveQueue()
        self._notifications = NotificationService(
            workdir=workdir, log_path=log_path,
            get_progress=lambda: self._distributor.get_progress(),
        )

        self._pool = pool or SessionPool(
            max_sessions=max_sessions,
            publisher=self.publisher,
            log_path=log_path,
            sleep_fn=sleep_fn,
        )

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
            failed_tasks=self._outcomes.failed_tasks,
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
            arbitrated_at_loop=self._outcomes.arbitrated_at_loop,
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
            return self._manager_loop()
        except KeyboardInterrupt:
            raise
        finally:
            self._shutdown_all()

    async def run_async(self, snapshot_publisher) -> int:
        return await asyncio.to_thread(self.run, snapshot_publisher)

    def shutdown(self) -> None:
        self._shutdown_all()

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
        card = create_inbox_card(board, text, log_path=self.log_path)
        self.publisher.log_inbox(card.id, text)

    def unblock_card(self, card_id: str, directive: str) -> None:
        board = self._distributor.board
        if unblock_card_uc(board, card_id, directive, log_path=self.log_path):
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

    # ── Manager loop ────────────────────────────────────────────

    def _manager_loop(self) -> int:
        quit_after_logged = False
        quit_after_last_status = 0.0
        while True:
            self._pool.reap_finished()
            self._publish_board_state()
            if is_stop_requested():
                return EXIT_INTERRUPT
            if is_quit_after_task_requested():
                if not quit_after_logged:
                    self.publisher._emit("system", "", "Quit-after-task: waiting for active agents to finish...")
                    quit_after_logged = True
                running = self._pool.running_info()
                now = time.time()
                if running:
                    if now - quit_after_last_status >= 10.0:
                        self.publisher._emit("system", "", f"Still working: {running}")
                        quit_after_last_status = now
                else:
                    self.publisher._emit("system", "", "All agents finished, exiting")
                    return EXIT_OK
            elif not self._pool.has_active():
                if self._distributor.has_remaining_work():
                    self._pool.restart_idle(target=self._run_worker)
                    if self._pool.has_active():
                        continue
                return EXIT_OK
            self.sleep_fn(MANAGER_POLL_SECONDS)

    def _publish_board_state(self) -> None:
        self._distributor.refresh()
        self.publisher.publish_board(self._distributor.board, self._pool.session_snapshots)
        self._flush_state_if_dirty()

    # ── State persistence ───────────────────────────────────────

    def mark_state_dirty(self) -> None:
        self._outcomes.mark_dirty()

    def _flush_state_if_dirty(self) -> None:
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

    def _shutdown_all(self) -> None:
        self._pool.shutdown_threads()
        # Kill any remaining child processes in our group.
        for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT", "SIGINT"):
            sig = getattr(signal, sig_name, None)
            if sig:
                try:
                    signal.signal(sig, signal.SIG_IGN)
                except Exception:
                    pass
        kill_own_process_group()
