#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban-mode session manager: teamlead + workers with pull-based role dispatch."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from argparse import Namespace
from pathlib import Path
from typing import Callable, Optional

from .backend import Backend, get_backend
from .integration_manager import IntegrationManager
from .kanban_incident_manager import IncidentManager
from .kanban_card import KanbanCard, new_card_body
from .kanban_distributor import KanbanDistributor
from .kanban_constants import (
    STAGE_DONE,
    STAGE_INBOX,
    STAGE_SHORT_NAMES,
    Action,
)
from .kanban_publisher import KanbanPublisher
from .kanban_request_builder import build_kanban_request
from .kanban_teamlead_runner import KanbanTeamleadRunner
from .kanban_worker_runner import KanbanWorkerRunner
from .notify import send_telegram_message
from .project_hooks import fire_hooks
from .kanban_roles import ROLE_TEAMLEAD
from .logging import log_event
from .quit_signal import is_quit_after_task_requested, is_session_stop_requested, is_stop_requested
from .session_types import (
    MANAGER_POLL_SECONDS,
    MAX_SESSIONS,
    SHUTDOWN_JOIN_TIMEOUT_SECONDS,
    STAGGER_DELAY_SECONDS,
    SessionSlot,
    SlotStatus,
    next_session_id,
)
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine
from .worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130


SnapshotPublisher = Callable[[str, Optional[MonitorSnapshot]], None]
_logger = logging.getLogger(__name__)


class KanbanSessionManager:
    """Orchestrates AI agents on a kanban board using a pull system."""

    def __init__(
        self,
        *,
        workdir: str,
        tasks_dir: Path,
        args: Namespace,
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
        self.args = args
        self.log_path = log_path
        self.engine = engine
        self.commit_template = commit_template
        self.merge_expert_template = merge_expert_template
        self.merge_expert_model = (merge_expert_model or "").strip()
        self.main_branch = (main_branch or "main").strip() or "main"
        self.max_sessions = max(2, min(max_sessions, MAX_SESSIONS))
        self.sleep_fn = sleep_fn

        self._distributor = KanbanDistributor(tasks_dir)
        self._integrator = IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
            safe_tracked_paths=frozenset(),
        )
        self._slots: dict[str, SessionSlot] = {}
        self._slots_lock = threading.Lock()
        self._worktree_lock = threading.Lock()

        self.snapshot_publisher: Optional[SnapshotPublisher] = None
        self.publisher = KanbanPublisher()
        self._session_snapshots: dict[str, MonitorSnapshot] = {}
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._completed_tasks: list[str] = []
        self._failed_tasks: list[str] = []
        self._incident_mgr: IncidentManager = None  # type: ignore[assignment]  # initialized after _slots
        self._card_fail_counts: dict[str, int] = {}  # card_id → consecutive failures
        self._arbitrated_at_loop: dict[str, int] = {}  # card_id → loop_count at last arbitration
        self._state_dirty: bool = False
        self._directive_queue: list[str] = []
        self._directive_lock = threading.Lock()
        self._telegram_available: bool | None = None  # cached telegram availability
        self._load_kanban_state()
        self._incident_mgr = IncidentManager(
            distributor=self._distributor,
            publisher=self.publisher,
            engine=self.engine,
            slots=self._slots,
            slots_lock=self._slots_lock,
            failed_tasks=self._failed_tasks,
            log_path=self.log_path,
            workdir=self.workdir,
            max_sessions=self.max_sessions,
            sleep_fn=self.sleep_fn,
            make_request_fn=self._make_request,
            add_session_fn=self.request_add_session,
            remove_session_fn=lambda sid: self.request_remove_session(sid),
        )
        self._worker_runner = KanbanWorkerRunner(
            workdir=self.workdir,
            log_path=self.log_path,
            engine=self.engine,
            distributor=self._distributor,
            publisher=self.publisher,
            args=self.args,
            main_branch=self.main_branch,
            slots_lock=self._slots_lock,
            worktree_lock=self._worktree_lock,
            card_fail_counts=self._card_fail_counts,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            make_request_fn=self._make_request,
            mark_state_dirty_fn=self._mark_state_dirty,
            send_telegram_fn=self._send_telegram,
            notify_completion_fn=self._notify_completion,
            should_continue_fn=self._should_continue,
            sleep_fn=self.sleep_fn,
        )
        self._teamlead_runner = KanbanTeamleadRunner(
            workdir=self.workdir,
            log_path=self.log_path,
            engine=self.engine,
            distributor=self._distributor,
            publisher=self.publisher,
            incident_mgr=self._incident_mgr,
            slots_lock=self._slots_lock,
            arbitrated_at_loop=self._arbitrated_at_loop,
            make_request_fn=self._make_request,
            mark_state_dirty_fn=self._mark_state_dirty,
            send_telegram_fn=self._send_telegram,
            should_continue_fn=self._should_continue,
            pop_directive_fn=self._pop_directive,
            sleep_fn=self.sleep_fn,
        )

    # ── State persistence ─────────────────────────────────────────

    def _load_kanban_state(self) -> None:
        """Load persisted card_fail_counts and arbitrated_at_loop from disk."""
        import json
        from .state_paths import kanban_state_path
        path = kanban_state_path(self.workdir)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._card_fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
            self._arbitrated_at_loop = {k: int(v) for k, v in data.get("arbitrated_at_loop", {}).items()}
        except Exception as exc:
            _logger.warning("Failed to load kanban state: %s", exc)

    def _save_kanban_state(self) -> None:
        """Persist card_fail_counts and arbitrated_at_loop to disk."""
        from .atomic_io import write_json_atomic
        from .state_paths import kanban_state_path
        path = kanban_state_path(self.workdir)
        write_json_atomic(path, {
            "card_fail_counts": self._card_fail_counts,
            "arbitrated_at_loop": self._arbitrated_at_loop,
        })
        self._state_dirty = False

    def _mark_state_dirty(self) -> None:
        self._state_dirty = True

    def _flush_state_if_dirty(self) -> None:
        if self._state_dirty:
            self._save_kanban_state()

    # ── Public API ──────────────────────────────────────────────

    def request_add_session(self) -> Optional[str]:
        return self._start_session(role="worker")

    def request_remove_session(self, session_id: str = "") -> None:
        with self._slots_lock:
            candidates = [s for s in self._slots.values()
                          if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)]
            if session_id:
                slot = next((s for s in candidates if s.session_id == session_id), None)
            else:
                slot = candidates[-1] if candidates else None
        if slot:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSING
            log_event(self.log_path, "INFO", "session closing", session_id=slot.session_id)

    def run(self, snapshot_publisher: SnapshotPublisher) -> int:
        self.snapshot_publisher = snapshot_publisher
        self._started_at = time.time()
        self.publisher.set_started_at(self._started_at)
        self._wire_board_callbacks()
        self._distributor.refresh()
        self._release_stale_agents()
        done, _ip, total = self._distributor.get_progress()
        self.publisher._emit("system", "", f"Kanban started: {total} cards, {self.max_sessions} agents")
        self._publish_board_state()
        self._integrator.recover_stale_git_state()
        self._start_session(role=ROLE_TEAMLEAD)
        self._publish_board_state()
        self.sleep_fn(STAGGER_DELAY_SECONDS)
        for _ in range(self.max_sessions - 1):
            if is_stop_requested():
                break
            self._start_session(role="worker")
            self.sleep_fn(STAGGER_DELAY_SECONDS)
        try:
            return self._manager_loop()
        except KeyboardInterrupt:
            raise
        finally:
            self._shutdown_all()

    async def run_async(self, snapshot_publisher: SnapshotPublisher) -> int:
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

    def _release_stale_agents(self) -> None:
        """Release cards stuck with assigned_agent from a crashed previous run."""
        board = self._distributor.board
        released = 0
        done_ids: set[str] = set()
        for card in list(board.cards):
            if card.stage == STAGE_DONE:
                done_ids.add(card.id)
            if card.assigned_agent and card.stage != STAGE_DONE:
                old_agent = card.assigned_agent
                board.release_agent(card)
                released += 1
                self.publisher._emit(
                    "system", card.id,
                    f"{card.id} released stale agent {old_agent}",
                )
                log_event(self.log_path, "INFO", "released stale agent",
                          task_id=card.id, old_agent=old_agent)
        if released:
            self.publisher._emit("system", "", f"Released {released} stale agent(s) from previous run")
        # Cleanup worktrees for cards that are Done
        self._cleanup_done_worktrees(done_ids)

    def _cleanup_done_worktrees(self, done_ids: set[str]) -> None:
        """Remove worktrees for cards that reached Done."""
        from .worktree_flow import _safe_name
        from .state_paths import worktrees_root
        wt_root = worktrees_root(self.workdir)
        if not wt_root.exists():
            return
        cleaned = 0
        for card_id in done_ids:
            safe = _safe_name(card_id)
            wt_path = wt_root / safe
            if wt_path.exists():
                from .worktree_flow import cleanup_task_worktree, WorktreeSession
                session = WorktreeSession(
                    base_workdir=self.workdir,
                    worktree_path=str(wt_path),
                    branch_name=f"orc/{safe}",
                    task_id=card_id,
                )
                try:
                    cleanup_task_worktree(session, self.log_path)
                    cleaned += 1
                except Exception as exc:
                    log_event(self.log_path, "WARN", "failed to cleanup done worktree",
                              task_id=card_id, error=str(exc)[:200])
        if cleaned:
            self.publisher._emit("system", "", f"Cleaned {cleaned} worktree(s) from completed cards")

    # ── Manager loop ─────────────────────────────────────────────

    def _manager_loop(self) -> int:
        quit_after_logged = False
        quit_after_last_status = 0.0
        while True:
            self._reap_finished_slots()
            self._publish_board_state()
            if is_stop_requested():
                return EXIT_INTERRUPT
            if is_quit_after_task_requested():
                if not quit_after_logged:
                    self.publisher._emit("system", "", "Quit-after-task: waiting for active agents to finish...")
                    quit_after_logged = True
                running = self._running_slots_info()
                now = time.time()
                if running:
                    if now - quit_after_last_status >= 10.0:
                        self.publisher._emit("system", "", f"Still working: {running}")
                        quit_after_last_status = now
                else:
                    self.publisher._emit("system", "", "All agents finished, exiting")
                    return EXIT_OK
            elif not self._has_active_slots():
                if self._distributor.has_remaining_work():
                    self._restart_idle_slots()
                    if self._has_active_slots():
                        continue
                return EXIT_OK
            self.sleep_fn(MANAGER_POLL_SECONDS)

    def _running_slots_info(self) -> str:
        with self._slots_lock:
            running = [s for s in self._slots.values() if s.status == SlotStatus.RUNNING and s.thread and s.thread.is_alive()]
        if not running:
            return ""
        # Show actual assignment status — only report active card if slot has a task
        parts = []
        for s in running:
            if s.task:
                parts.append(f"{s.session_id}({s.task.text})")
            else:
                parts.append(f"{s.session_id}(idle)")
        return ", ".join(parts)

    def _publish_board_state(self) -> None:
        self._distributor.refresh()
        self.publisher.publish_board(self._distributor.board, self._session_snapshots)
        self._flush_state_if_dirty()

    def _has_active_slots(self) -> bool:
        with self._slots_lock:
            return any(s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
                       for s in self._slots.values())

    def _reap_finished_slots(self) -> None:
        with self._slots_lock:
            for slot in self._slots.values():
                if slot.thread and not slot.thread.is_alive() and slot.status == SlotStatus.RUNNING:
                    slot.status = SlotStatus.CLOSED
                    slot.thread = None

    def _restart_idle_slots(self) -> None:
        with self._slots_lock:
            closed = [s for s in self._slots.values() if s.status == SlotStatus.CLOSED]
        for slot in closed:
            self._launch_slot_thread(slot)

    # ── Session lifecycle ────────────────────────────────────────

    def _start_session(self, role: str = "worker") -> Optional[str]:
        with self._slots_lock:
            active = sum(1 for s in self._slots.values()
                         if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING, SlotStatus.CLOSING))
            if active >= self.max_sessions:
                self.publisher._emit("system", "", f"Cannot add agent: {active}/{self.max_sessions} slots used")
                return None
            sid = next_session_id()
            slot = SessionSlot(session_id=sid)
            self._slots[sid] = slot
        slot.role = role
        self._launch_slot_thread(slot)
        self.publisher._emit("system", "", f"{sid} session created (role={role})")
        if self.snapshot_publisher:
            self.snapshot_publisher(sid, None)
        log_event(self.log_path, "INFO", "kanban session started", session_id=sid, role=role)
        return sid

    def _launch_slot_thread(self, slot: SessionSlot) -> None:
        role = slot.role or "worker"
        target = self._run_teamlead if role == ROLE_TEAMLEAD else self._run_worker
        thread = threading.Thread(target=target, args=(slot,), daemon=True,
                                  name=f"kanban-{slot.session_id}")
        with self._slots_lock:
            slot.thread = thread
            slot.status = SlotStatus.RUNNING
        thread.start()

    # ── Worker thread ────────────────────────────────────────────

    def _run_worker(self, slot: SessionSlot) -> None:
        self._worker_runner.run(slot)

    # ── Teamlead thread ──────────────────────────────────────────

    def _run_teamlead(self, slot: SessionSlot) -> None:
        self._teamlead_runner.run(slot)

    # ── Teamlead helpers (kept in manager) ─────────────────────────

    def _pop_directive(self) -> Optional[str]:
        with self._directive_lock:
            if self._directive_queue:
                return self._directive_queue.pop(0)
        return None

    def _send_telegram(self, message: str) -> None:
        """Send telegram message."""
        send_telegram_message(message, self.log_path, orc_root=Path(self.workdir))

    def _notify_completion(
        self, card: KanbanCard, role: str,
        old_stage: str, old_action: str, old_cos: str,
        elapsed: float,
    ) -> None:
        """Send a single rich Telegram notification after a role finishes."""
        mins = elapsed / 60.0
        new_stage = card.stage
        new_action = card.action

        # Only notify on meaningful transitions, not every micro-step
        # Notify: stage changed, or expedite flagged, or Done
        stage_changed = old_stage != new_stage
        became_expedite = card.class_of_service == "expedite" and old_cos != "expedite"
        is_done = new_stage == STAGE_DONE

        if not stage_changed and not became_expedite:
            return

        # Build short stage names for readability
        fr = STAGE_SHORT_NAMES.get(old_stage, old_stage)
        to = STAGE_SHORT_NAMES.get(new_stage, new_stage)

        icon = "✅" if is_done else "🔄"
        if became_expedite:
            icon = "🔥"

        lines = [f"{icon} {card.id}: {card.title}"]
        lines.append(f"  {role} ({mins:.0f}m): {fr} → {to}")
        if old_action != new_action:
            lines.append(f"  Action: {old_action} → {new_action}")
        if became_expedite:
            lines.append(f"  EXPEDITE: {card.cos_justification or 'no reason'}")

        # For Done cards — extract delivery summary from card body
        if is_done:
            summary = self._extract_card_summary(card)
            if summary:
                lines.append(f"\n{summary}")

        done, _ip, total = self._distributor.get_progress()
        lines.append(f"\nProgress: {done}/{total}")

        self._send_telegram("\n".join(lines))

        fire_hooks(self.workdir, "on_complete", {
            "ORC_CARD_ID": card.id,
            "ORC_CARD_TITLE": card.title,
            "ORC_FROM_STAGE": fr,
            "ORC_TO_STAGE": to,
            "ORC_ROLE": role,
            "ORC_REASON": f"{old_action} -> {new_action}",
            "ORC_ELAPSED_MIN": f"{mins:.1f}",
        })

    @staticmethod
    def _extract_card_summary(card: KanbanCard) -> str:
        """Extract last implementation/integration note block from card body."""
        body = card.body or ""
        # Find section 3 content
        in_section3 = False
        section3_lines: list[str] = []
        for line in body.splitlines():
            if line.startswith("# 3."):
                in_section3 = True
                continue
            if in_section3 and line.startswith("# "):
                break
            if in_section3:
                section3_lines.append(line)
        if not section3_lines:
            return ""
        # Take last non-empty paragraph (integrator's summary is appended last)
        text = "\n".join(section3_lines).strip()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return ""
        last = paragraphs[-1]
        # Truncate for telegram readability
        if len(last) > 500:
            last = last[:497] + "..."
        return last

    # ── Request builder ──────────────────────────────────────────

    def _make_request(self, task, prompt, workdir, session_id, commit_phase, task_ttl):
        def _pub(snapshot: MonitorSnapshot) -> None:
            self._session_snapshots[session_id] = snapshot
            if self.snapshot_publisher:
                self.snapshot_publisher(session_id, snapshot)
        return build_kanban_request(
            task=task, prompt=prompt, workdir=workdir, base_workdir=self.workdir,
            tasks_dir=self.tasks_dir, session_id=session_id, commit_phase=commit_phase,
            task_ttl=task_ttl, args=self.args, backend=self.backend,
            commit_template=self.commit_template, merge_expert_template=self.merge_expert_template,
            merge_expert_model=self.merge_expert_model, main_branch=self.main_branch,
            progress=self._distributor.get_progress(), snapshot_publisher=_pub,
        )

    # ── Inbox ────────────────────────────────────────────────────

    def add_inbox_card(self, text: str) -> None:
        board = self._distributor.board
        card_id = board.next_card_id()
        card = board.create_inbox_card(card_id, text)
        self.publisher.log_inbox(card_id, text)
        log_event(self.log_path, "INFO", "inbox card created", card_id=card_id, title=text)

    # ── Human-in-the-loop ─────────────────────────────────────────

    def unblock_card(self, card_id: str, directive: str) -> None:
        """Unblock a card and send it back to Coding with a directive."""
        board = self._distributor.board
        card = board.card_by_id(card_id)
        if card is None:
            return
        if card.action != Action.BLOCKED:
            return
        if directive:
            card.body += f"\n\n## Human Directive\n{directive}\n"
        card.action = Action.CODING
        card.loop_count = 0
        board.save_card(card)
        self.publisher.log_unblock(card_id, directive)
        log_event(self.log_path, "INFO", "card unblocked", card_id=card_id, directive=directive)

    def queue_teamlead_directive(self, text: str) -> None:
        """Queue a user directive for the teamlead to process."""
        with self._directive_lock:
            self._directive_queue.append(text)
        self.publisher._emit("directive", "", f"Directive queued for teamlead: {text}")
        log_event(self.log_path, "INFO", "teamlead directive queued", directive=text[:200])

    # ── Helpers ──────────────────────────────────────────────────

    def _should_continue(self, slot: SessionSlot) -> bool:
        return (not is_stop_requested()
                and not is_session_stop_requested(slot.session_id)
                and slot.status != SlotStatus.CLOSING)

    def _board_diag_short(self) -> str:
        """One-line board summary for diagnostics."""
        board = self._distributor.board
        inbox = board.cards_in_stage(STAGE_INBOX)
        free_inbox = sum(1 for c in inbox if not c.assigned_agent)
        total_assigned = sum(1 for c in board.cards if c.assigned_agent)
        return f"inbox={len(inbox)} (free={free_inbox}), assigned_total={total_assigned}"

    def _shutdown_all(self) -> None:
        with self._slots_lock:
            for s in self._slots.values():
                s.status = SlotStatus.CLOSING
            threads = [(s.session_id, s.thread) for s in self._slots.values() if s.thread]
        total = len(threads)
        if total:
            self.publisher._emit("system", "", f"Shutting down {total} agents...")
        for i, (sid, t) in enumerate(threads, 1):
            self.publisher._emit("system", "", f"Waiting for {sid} ({i}/{total})...")
            t.join(timeout=SHUTDOWN_JOIN_TIMEOUT_SECONDS)
            if t.is_alive():
                self.publisher._emit("system", "", f"{sid} still running, skipping")
            else:
                self.publisher._emit("system", "", f"{sid} stopped ({total - i} remaining)")
        if total:
            self.publisher._emit("system", "", "All agents stopped")
