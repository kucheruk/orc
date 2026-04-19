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

from ...git.integration_manager import IntegrationManager
from ...git.branch_resolver import DEFAULT_MAIN_BRANCH
from ...board.kanban_distributor import KanbanDistributor
from ...board.stage_constants import STAGE_INBOX
from ...config import OrcConfig
from ..infra.board_event_bridge import BoardEventBridge
from ..infra.directive_queue import DirectiveQueue
from ..infra.notification_service import NotificationService
from ..infra.publisher import KanbanPublisher
from ..infra.request_factory import KanbanRequestFactory
from .state_persistence import (
    cleanup_done_worktrees,
    cleanup_stale_parallel_sessions,
    release_stale_agents,
)
from ..runners.teamlead import KanbanTeamleadRunner
from ..runners.worker import KanbanWorkerRunner
from ...board.kanban_role_registry import ROLE_TEAMLEAD
from ...board.kanban_board_health import detect_circular_deps
from ...board.action_constants import Action
from ...board.stage_constants import STAGE_DONE, STAGE_ESTIMATE
from ...log import log_event
from ...quit_signal import is_quit_after_task_requested, is_stop_requested
from .pool import SessionPool
from ...tasks.completion.outcomes import TaskOutcomeTracker
from .types import (
    MANAGER_POLL_SECONDS,
    STAGGER_DELAY_SECONDS,
    SessionSlot,
)
from ...tasks.ports import ProcessLifecyclePort

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
        distributor: KanbanDistributor,
        integrator: IntegrationManager,
        publisher: KanbanPublisher,
        pool: SessionPool,
        outcomes: TaskOutcomeTracker,
        directives: DirectiveQueue,
        notifications: NotificationService,
        board_events: BoardEventBridge,
        request_factory: KanbanRequestFactory,
        worker_runner: KanbanWorkerRunner,
        teamlead_runner: KanbanTeamleadRunner,
        process_lifecycle: ProcessLifecyclePort,
        main_branch: str = DEFAULT_MAIN_BRANCH,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.workdir = workdir
        self.tasks_dir = tasks_dir
        self.config = config
        self.log_path = log_path
        self.main_branch = main_branch  # already resolved by composition root
        self.sleep_fn = sleep_fn

        self._distributor = distributor
        self._integrator = integrator

        self.publisher = publisher
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._outcomes = outcomes
        self._directives = directives
        self._notifications = notifications
        self._pool = pool
        self._last_heartbeat_at = 0.0
        self._idle_since: float = 0.0
        self._last_idle_emit_at: float = 0.0
        self._last_heartbeat_log_offset = self.log_path.stat().st_size if self.log_path.exists() else 0

        self._board_events = board_events
        self._request_factory = request_factory
        self._worker_runner = worker_runner
        self._teamlead_runner = teamlead_runner
        self._process_lifecycle = process_lifecycle

    # ── Public API ──────────────────────────────────────────────

    def request_add_session(self) -> Optional[str]:
        return self._pool.request_add(target=self._run_worker)

    def request_remove_session(self, session_id: str = "") -> None:
        self._pool.request_remove(session_id)

    def run(self, snapshot_publisher) -> int:
        self._pool.snapshot_publisher = snapshot_publisher
        self._started_at = time.time()
        self.publisher.set_started_at(self._started_at)
        self._board_events.wire()
        self._distributor.refresh()

        # Cleanup stale state from previous runs
        cleanup_ids = release_stale_agents(self._distributor.board, self.publisher)
        cleanup_done_worktrees(cleanup_ids, self.workdir, self.log_path, self.publisher)
        cleanup_stale_parallel_sessions(
            self._distributor.board, self.workdir, self.log_path, self.publisher,
        )

        done, _ip, total = self._distributor.get_progress()
        self.publisher.emit("system", "", f"Kanban started: {total} cards, {self._pool.max_sessions} agents")
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
                on_tick=self._on_tick,
                sleep_fn=self.sleep_fn,
            )
        except KeyboardInterrupt:
            raise
        finally:
            _shutdown_all(self._pool, self._process_lifecycle)

    async def run_async(self, snapshot_publisher) -> int:
        return await asyncio.to_thread(self.run, snapshot_publisher)

    def shutdown(self) -> None:
        _shutdown_all(self._pool, self._process_lifecycle)

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

    @property
    def board(self):
        """Expose the underlying kanban board for delivery layers (TUI/CLI)."""
        return self._distributor.board

    def queue_teamlead_directive(self, text: str) -> None:
        self._directives.push(text)
        self.publisher.emit("directive", "", f"Directive queued for teamlead: {text}")
        log_event(self.log_path, "INFO", "teamlead directive queued", directive=text[:200])

    # ── State persistence ───────────────────────────────────────

    def mark_state_dirty(self) -> None:
        self._outcomes.mark_dirty()

    def _publish_board_state(self) -> None:
        self._board_events.publish_board_state()

    # ── Worker/teamlead thread targets ──────────────────────────

    def _run_worker(self, slot: SessionSlot) -> None:
        self._worker_runner.run(slot)

    def _run_teamlead(self, slot: SessionSlot) -> None:
        self._teamlead_runner.run(slot)

    # ── Helpers ──────────────────────────────────────────────────

    def _pop_directive(self) -> Optional[str]:
        return self._directives.pop()

    def _send_telegram(self, message: str) -> None:
        """Raw telegram send — for legacy paths. Prefer a severity-aware
        formatter via NotificationService for new call sites."""
        self._notifications.send_telegram(message)

    def _on_tick(self) -> None:
        self._maybe_send_heartbeat()
        self._maybe_emit_idle_window()

    _IDLE_WINDOW_THRESHOLD_SECONDS = 60.0
    _IDLE_WINDOW_DEBOUNCE_SECONDS = 300.0

    def _maybe_emit_idle_window(self) -> None:
        """Emit a single WARN event when every worker slot has been idle long
        enough that a supervisor can safely stop ORC (no attempt mid-flight).

        Lightweight hook for external supervisors (me / Claude / any sidecar)
        to listen on via ``tail -F orc.log | grep "orc idle window"``. No file
        writes or IPC — just one log line, debounced so repeated idle ticks
        don't flood.
        """
        running = self._pool.running_info()
        now = time.time()
        if running:
            if self._idle_since:
                self._idle_since = 0.0
            return
        if self._idle_since == 0.0:
            self._idle_since = now
            return
        duration = now - self._idle_since
        if duration < self._IDLE_WINDOW_THRESHOLD_SECONDS:
            return
        if (now - self._last_idle_emit_at) < self._IDLE_WINDOW_DEBOUNCE_SECONDS:
            return
        self._last_idle_emit_at = now
        from ...log import log_event
        log_event(
            self.log_path,
            "WARN",
            "orc idle window",
            idle_seconds=int(duration),
            threshold_seconds=int(self._IDLE_WINDOW_THRESHOLD_SECONDS),
            pool_running="",
            hint="supervisor may safely restart ORC now",
        )
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.ORC_IDLE_WINDOW,
            "worker_slots_idle",
            context={"idle_seconds": int(duration)},
        )

    def _send_heartbeat_telegram(self, message: str) -> None:
        """Heartbeat pings are routine — only surface them in debug mode."""
        from ...notifications.messages import Severity
        from ...notifications.notify import send_severity
        send_severity((Severity.INFO, message), self._notifications._log_path,
                      orc_root=Path(self.workdir))

    def _notify_completion(self, card, role, old_stage, old_action, old_cos, elapsed) -> None:
        self._notifications.notify_completion(card, role, old_stage, old_action, old_cos, elapsed)

    def make_request(self, task, prompt, workdir, session_id, commit_phase, task_ttl):
        return self._request_factory.make(
            task=task,
            prompt=prompt,
            workdir=workdir,
            session_id=session_id,
            commit_phase=commit_phase,
            task_ttl=task_ttl,
        )

    def _board_diag_short(self) -> str:
        board = self._distributor.board
        inbox = board.cards_in_stage(STAGE_INBOX)
        free_inbox = sum(1 for c in inbox if not c.assigned_agent)
        total_assigned = sum(1 for c in board.cards if c.assigned_agent)
        return f"inbox={len(inbox)} (free={free_inbox}), assigned_total={total_assigned}"

    def _maybe_send_heartbeat(self) -> None:
        interval = max(float(getattr(self.config, "report_interval", 180.0) or 180.0), 30.0)
        now = time.time()
        if now - self._last_heartbeat_at < interval:
            return
        self._last_heartbeat_at = now

        done, in_progress, total = self._distributor.get_progress()
        stage_summary = self._distributor.board.summary()
        stage_counts = ", ".join(
            f"{stage}={meta.get('count', 0)}"
            for stage, meta in stage_summary.items()
        )
        blocked_by_deps = self._blocked_by_deps_count()
        cycles = self._cycle_count()
        ready_frontier = self._ready_frontier_cards(limit=4)
        auto_unblock_events = self._count_recent_auto_unblock_events()
        running = self._pool.running_info() or "none"
        elapsed = max(int(now - self._started_at), 0)
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        elapsed_str = f"{hours}h{mins:02d}m{secs:02d}s" if hours else f"{mins}m{secs:02d}s"
        message = (
            "ORC heartbeat\n"
            f"Workspace: {self.workdir}\n"
            f"Board: {done}/{total} done, in_progress={in_progress}\n"
            f"Stages: {stage_counts}\n"
            f"Flow: blocked_by_deps={blocked_by_deps}, cycles={cycles}, auto_unblock_events={auto_unblock_events}\n"
            f"Ready frontier: {ready_frontier}\n"
            f"Workers: {running}\n"
            f"Uptime: {elapsed_str}"
        )
        self._send_heartbeat_telegram(message)

    def _blocked_by_deps_count(self) -> int:
        board = self._distributor.board
        return sum(
            1
            for card in board.cards
            if card.stage == STAGE_ESTIMATE and card.action == Action.CODING and board.has_unmet_dependencies(card)
        )

    def _cycle_count(self) -> int:
        board = self._distributor.board
        active = [c for c in board.cards if c.stage != STAGE_DONE]
        done_ids = {c.id for c in board.cards if c.stage == STAGE_DONE}
        diag = detect_circular_deps(active, done_ids)
        return 1 if diag else 0

    def _ready_frontier_cards(self, *, limit: int = 4) -> str:
        board = self._distributor.board
        ready = []
        for card in board.cards:
            if card.stage == STAGE_DONE or card.assigned_agent:
                continue
            if board.has_unmet_dependencies(card):
                continue
            ready.append(card.id)
        return ", ".join(ready[:limit]) if ready else "none"

    def _count_recent_auto_unblock_events(self) -> int:
        if not self.log_path.exists():
            return 0
        count = 0
        with self.log_path.open("r", encoding="utf-8", errors="ignore") as handle:
            try:
                handle.seek(self._last_heartbeat_log_offset)
            except OSError:
                handle.seek(0)
            for line in handle:
                if "teamlead auto-unblock" in line:
                    count += 1
            self._last_heartbeat_log_offset = handle.tell()
        return count



# ── Standalone orchestration functions ──────────────────────────


def _manager_loop(
    *,
    pool: SessionPool,
    distributor: KanbanDistributor,
    publisher: KanbanPublisher,
    publish_board: Callable[[], None],
    run_worker: Callable,
    on_tick: Callable[[], None],
    sleep_fn: Callable[[float], None],
) -> int:
    """Main event loop: reap finished sessions, check exit conditions, restart idle workers."""
    quit_after_logged = False
    quit_after_last_status = 0.0
    while True:
        pool.reap_finished()
        publish_board()
        on_tick()
        if is_stop_requested():
            return EXIT_INTERRUPT
        if is_quit_after_task_requested():
            if not quit_after_logged:
                publisher.emit("system", "", "Quit-after-task: waiting for active agents to finish...")
                quit_after_logged = True
            running = pool.running_info()
            now = time.time()
            if running:
                if now - quit_after_last_status >= 10.0:
                    publisher.emit("system", "", f"Still working: {running}")
                    quit_after_last_status = now
            else:
                publisher.emit("system", "", "All agents finished, exiting")
                return EXIT_OK
        elif not pool.has_active():
            if distributor.has_remaining_work():
                pool.restart_idle(target=run_worker)
                if pool.has_active():
                    continue
            return EXIT_OK
        sleep_fn(MANAGER_POLL_SECONDS)


def _shutdown_all(pool: SessionPool, lifecycle: ProcessLifecyclePort) -> None:
    """Shutdown all session threads and kill child processes."""
    pool.shutdown_threads()
    for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT", "SIGINT"):
        sig = getattr(signal, sig_name, None)
        if sig:
            try:
                signal.signal(sig, signal.SIG_IGN)
            except Exception:
                pass
    lifecycle.kill_own_group()
