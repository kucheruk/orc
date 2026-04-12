#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban-mode session manager: teamlead + workers with pull-based role dispatch."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from ..infra.backend import Backend, get_backend
from ..git.integration_manager import IntegrationManager
from .kanban_incident_manager import IncidentManager
from ..board.kanban_card import KanbanCard, new_card_body
from ..board.kanban_distributor import KanbanDistributor
from ..board.kanban_constants import (
    STAGE_DONE,
    STAGE_INBOX,
    STAGE_SHORT_NAMES,
    Action,
)
from ..board.kanban_notifications import extract_card_summary, format_completion_message
from ..cli.orc_config import OrcConfig
from .kanban_publisher import KanbanPublisher
from .kanban_request_builder import build_kanban_request
from .kanban_protocols import (
    CompletionNotifier,
    DirectiveSource,
    RunnerLifecycle,
    RunnerNotifier,
    RunnerStateManager,
    SessionController,
)
from .kanban_teamlead_runner import KanbanTeamleadRunner
from .kanban_worker_runner import KanbanWorkerRunner
from ..notifications.notify import send_telegram_message
from ..git.project_hooks import fire_hooks
from .kanban_roles import ROLE_TEAMLEAD
from ..infra.logging import log_event
from ..infra.quit_signal import is_quit_after_task_requested, is_stop_requested
from .session_pool import SessionPool
from .session_types import (
    MANAGER_POLL_SECONDS,
    STAGGER_DELAY_SECONDS,
    SessionSlot,
)
from ..infra.monitor_types import MonitorSnapshot
from ..tasks.task_execution import TaskExecutionEngine
from ..git.worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree
from ..infra.atomic_io import write_json_atomic
from ..infra.process_groups import kill_own_process_group
from ..infra.state_paths import kanban_state_path

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130


_logger = logging.getLogger(__name__)


# ── Standalone helpers ──────────────────────────────────────────────


def _load_kanban_state(workdir: str) -> tuple[dict[str, int], dict[str, int]]:
    """Load persisted card_fail_counts and arbitrated_at_loop from disk."""
    path = kanban_state_path(workdir)
    if not path.exists():
        return {}, {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
        arb_loop = {k: int(v) for k, v in data.get("arbitrated_at_loop", {}).items()}
        return fail_counts, arb_loop
    except Exception as exc:
        _logger.warning("Failed to load kanban state: %s", exc)
        return {}, {}


def _save_kanban_state(
    workdir: str,
    card_fail_counts: dict[str, int],
    arbitrated_at_loop: dict[str, int],
) -> None:
    """Persist card_fail_counts and arbitrated_at_loop to disk."""
    path = kanban_state_path(workdir)
    write_json_atomic(path, {
        "card_fail_counts": card_fail_counts,
        "arbitrated_at_loop": arbitrated_at_loop,
    })


def _release_stale_agents(board, publisher) -> set[str]:
    """Release cards stuck with assigned_agent from a crashed previous run.

    Returns set of done card IDs (for worktree cleanup).
    """
    released = 0
    done_ids: set[str] = set()
    for card in list(board.cards):
        if card.stage == STAGE_DONE:
            done_ids.add(card.id)
        if card.assigned_agent and card.stage != STAGE_DONE:
            old_agent = card.assigned_agent
            board.release_agent(card)
            released += 1
            publisher._emit("system", card.id, f"{card.id} released stale agent {old_agent}")
    if released:
        publisher._emit("system", "", f"Released {released} stale agent(s) from previous run")
    return done_ids


def _cleanup_done_worktrees(
    done_ids: set[str], workdir: str, log_path: Path, publisher,
) -> None:
    """Remove worktrees for cards that reached Done."""
    from ..git.worktree_flow import _safe_name
    from ..infra.state_paths import worktrees_root
    wt_root = worktrees_root(workdir)
    if not wt_root.exists():
        return
    cleaned = 0
    for card_id in done_ids:
        safe = _safe_name(card_id)
        wt_path = wt_root / safe
        if wt_path.exists():
            session = WorktreeSession(
                base_workdir=workdir,
                worktree_path=str(wt_path),
                branch_name=f"orc/{safe}",
                task_id=card_id,
            )
            try:
                cleanup_task_worktree(session, log_path)
                cleaned += 1
            except Exception as exc:
                log_event(log_path, "WARN", "failed to cleanup done worktree",
                          task_id=card_id, error=str(exc)[:200])
    if cleaned:
        publisher._emit("system", "", f"Cleaned {cleaned} worktree(s) from completed cards")


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

        self._distributor = KanbanDistributor(tasks_dir)
        self._integrator = IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
            safe_tracked_paths=frozenset(),
        )
        self._worktree_lock = threading.Lock()

        self.publisher = KanbanPublisher()
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._completed_tasks: list[str] = []
        self._failed_tasks: list[str] = []
        self._card_fail_counts, self._arbitrated_at_loop = _load_kanban_state(workdir)
        self._state_dirty: bool = False
        self._directive_queue: list[str] = []
        self._directive_lock = threading.Lock()

        # ── Session pool ────────────────────────────────────────
        self._pool = SessionPool(
            max_sessions=max_sessions,
            publisher=self.publisher,
            log_path=log_path,
            sleep_fn=sleep_fn,
        )

        # ── Protocol adapters ───────────────────────────────────
        self._lifecycle_adapter = _LifecycleAdapter(self._pool)
        self._notifier_adapter = _NotifierAdapter(self)
        self._state_adapter = _StateManagerAdapter(self)
        self._directive_adapter = _DirectiveAdapter(self)
        self._session_ctrl_adapter = _SessionControllerAdapter(self)

        self._incident_mgr = IncidentManager(
            distributor=self._distributor,
            publisher=self.publisher,
            engine=self.engine,
            slots=self._pool.slots,
            slots_lock=self._pool.slots_lock,
            failed_tasks=self._failed_tasks,
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
            card_fail_counts=self._card_fail_counts,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
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
            arbitrated_at_loop=self._arbitrated_at_loop,
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
        done_ids = _release_stale_agents(self._distributor.board, self.publisher)
        _cleanup_done_worktrees(done_ids, self.workdir, self.log_path, self.publisher)

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
        lines = [f"Completed: {len(self._completed_tasks)} tasks in {time_str}"]
        if self._completed_tasks:
            lines.append(f"  Tasks: {', '.join(self._completed_tasks)}")
        if self._failed_tasks:
            lines.append(f"  Failed: {', '.join(self._failed_tasks)}")
        lines.append(f"  Board: {done}/{total} done")
        return "\n".join(lines)

    def add_inbox_card(self, text: str) -> None:
        board = self._distributor.board
        card_id = board.next_card_id()
        board.create_inbox_card(card_id, text)
        self.publisher.log_inbox(card_id, text)
        log_event(self.log_path, "INFO", "inbox card created", card_id=card_id, title=text)

    def unblock_card(self, card_id: str, directive: str) -> None:
        board = self._distributor.board
        card = board.card_by_id(card_id)
        if card is None or card.action != Action.BLOCKED:
            return
        card.unblock(directive)
        board.save_card(card)
        self.publisher.log_unblock(card_id, directive)
        log_event(self.log_path, "INFO", "card unblocked", card_id=card_id, directive=directive)

    def queue_teamlead_directive(self, text: str) -> None:
        with self._directive_lock:
            self._directive_queue.append(text)
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

        board.on_move = _on_move
        board.on_action_change = lambda cid, old, new, role: self.publisher.log_action_change(cid, old, new, role)

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

    def _mark_state_dirty(self) -> None:
        self._state_dirty = True

    def _flush_state_if_dirty(self) -> None:
        if self._state_dirty:
            _save_kanban_state(self.workdir, self._card_fail_counts, self._arbitrated_at_loop)
            self._state_dirty = False

    # ── Worker/teamlead thread targets ──────────────────────────

    def _run_worker(self, slot: SessionSlot) -> None:
        self._worker_runner.run(slot)

    def _run_teamlead(self, slot: SessionSlot) -> None:
        self._teamlead_runner.run(slot)

    # ── Helpers ──────────────────────────────────────────────────

    def _pop_directive(self) -> Optional[str]:
        with self._directive_lock:
            if self._directive_queue:
                return self._directive_queue.pop(0)
        return None

    def _send_telegram(self, message: str) -> None:
        send_telegram_message(message, self.log_path, orc_root=Path(self.workdir))

    def _notify_completion(
        self, card: KanbanCard, role: str,
        old_stage: str, old_action: str, old_cos: str,
        elapsed: float,
    ) -> None:
        msg = format_completion_message(
            card, role, old_stage, old_action, old_cos, elapsed,
            self._distributor.get_progress(),
        )
        if msg:
            self._send_telegram(msg)

        fr = STAGE_SHORT_NAMES.get(old_stage, old_stage)
        to = STAGE_SHORT_NAMES.get(card.stage, card.stage)
        fire_hooks(self.workdir, "on_complete", {
            "ORC_CARD_ID": card.id,
            "ORC_CARD_TITLE": card.title,
            "ORC_FROM_STAGE": fr,
            "ORC_TO_STAGE": to,
            "ORC_ROLE": role,
            "ORC_REASON": f"{old_action} -> {card.action}",
            "ORC_ELAPSED_MIN": f"{elapsed / 60.0:.1f}",
        })

    def _make_request(self, task, prompt, workdir, session_id, commit_phase, task_ttl):
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


# ── Protocol adapter classes ───────────────────────────────────────


class _LifecycleAdapter:
    """Implements RunnerLifecycle by delegating to SessionPool."""

    __slots__ = ("_pool",)

    def __init__(self, pool: SessionPool) -> None:
        self._pool = pool

    def should_continue(self, slot) -> bool:
        return self._pool.should_continue(slot)

    def sleep(self, seconds: float) -> None:
        self._pool.sleep_fn(seconds)


class _NotifierAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def send_telegram(self, message: str) -> None:
        self._mgr._send_telegram(message)

    def notify_completion(self, card, role, old_stage, old_action, old_cos, elapsed) -> None:
        self._mgr._notify_completion(card, role, old_stage, old_action, old_cos, elapsed)


class _StateManagerAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def mark_dirty(self) -> None:
        self._mgr._mark_state_dirty()

    def make_request(self, task, prompt, workdir, session_id, commit_phase, ttl):
        return self._mgr._make_request(task, prompt, workdir, session_id, commit_phase, ttl)


class _DirectiveAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def pop_directive(self):
        return self._mgr._pop_directive()


class _SessionControllerAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def add_session(self):
        return self._mgr.request_add_session()

    def remove_session(self, session_id: str) -> None:
        self._mgr.request_remove_session(session_id)
