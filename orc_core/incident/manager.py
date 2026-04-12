#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incident state machine: detect worker crashes, triage, inject fix, scale workers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from ..board.action_constants import Action
from ..log import log_event
from ..notifications.notify import send_telegram_message
from ..quit_signal import is_stop_requested
from ..models.session_types import (
    STAGGER_DELAY_SECONDS,
    SessionSlot,
    SlotStatus,
)
from .phases import (
    handle_inject_fix,
    handle_notify_human,
    handle_scale_down,
    handle_scale_up,
    handle_triage,
    handle_wait_for_fix,
)
from .domain import (
    SCALE_DOWN_WAIT_TIMEOUT,
    Incident,
    IncidentPhase,
)

from ..agents.task_outcome_tracker import TaskOutcomeTracker
from .kanban_protocols import RunnerStateManager, SessionController

if TYPE_CHECKING:
    import threading

    from ..board.kanban_distributor import KanbanDistributor
    from .kanban_publisher import KanbanPublisher
    from .kanban_protocols import TaskExecutor


class IncidentManager:
    """Incident state machine extracted from KanbanSessionManager.

    Handles: detect_anomaly → scale_down → triage → inject_fix → wait_for_fix → scale_up.
    """

    def __init__(
        self,
        *,
        distributor: KanbanDistributor,
        publisher: KanbanPublisher,
        engine: "TaskExecutor",
        slots: dict[str, SessionSlot],
        slots_lock: threading.Lock,
        outcomes: TaskOutcomeTracker,
        log_path: Path,
        workdir: str,
        max_sessions: int,
        sleep_fn: Callable[[float], None],
        state_manager: RunnerStateManager,
        session_controller: SessionController,
    ) -> None:
        self._distributor = distributor
        self.publisher = publisher
        self.engine = engine
        self._slots = slots
        self._slots_lock = slots_lock
        self._outcomes = outcomes
        self.log_path = log_path
        self.workdir = workdir
        self.max_sessions = max_sessions
        self.sleep_fn = sleep_fn
        self._state_manager = state_manager
        self._session_controller = session_controller

        self._incident_counter: int = 0
        self._handled_crash_slots: set[str] = set()

    # ── Detection ────────────────────────────────────────────────

    def detect_anomaly(self) -> Optional[Incident]:
        """Check for crashed workers. Returns Incident or None."""
        with self._slots_lock:
            for slot in self._slots.values():
                if (slot.error
                        and slot.status == SlotStatus.CLOSED
                        and slot.session_id not in self._handled_crash_slots):
                    self._handled_crash_slots.add(slot.session_id)
                    self._incident_counter += 1
                    task_id = slot.task.task_id if slot.task else ""
                    wt_path = slot.worktree.worktree_path if slot.worktree else ""
                    return Incident(
                        id=f"INC-{self._incident_counter:03d}",
                        phase=IncidentPhase.SCALE_DOWN,
                        error_type="worker_crash",
                        source_task_id=task_id,
                        source_slot_id=slot.session_id,
                        error_message=slot.error,
                        traceback=slot.crash_traceback,
                        worktree_path=wt_path,
                    )
        return None

    # ── State machine dispatcher ─────────────────────────────────

    def process_incident(self, slot: SessionSlot, incident: Incident) -> Optional[Incident]:
        """Process one step of the incident state machine.

        Phase handlers are standalone functions in incident_phases.py.
        """
        _PHASE_DISPATCH = {
            IncidentPhase.SCALE_DOWN: lambda: handle_scale_down(self, incident),
            IncidentPhase.TRIAGE: lambda: handle_triage(self, slot, incident),
            IncidentPhase.INJECT_FIX: lambda: handle_inject_fix(self, incident),
            IncidentPhase.WAIT_FOR_FIX: lambda: handle_wait_for_fix(self, incident),
            IncidentPhase.SCALE_UP: lambda: handle_scale_up(self, incident),
            IncidentPhase.NOTIFY_HUMAN: lambda: handle_notify_human(self, incident),
        }
        handler = _PHASE_DISPATCH.get(incident.phase)
        if handler is None:
            log_event(self.log_path, "ERROR", "unknown incident phase",
                      incident_id=incident.id, phase=str(incident.phase))
            return None
        return handler()

    # ── Context API (used by phase handlers) ─────────────────────

    @property
    def distributor(self):
        return self._distributor

    @property
    def state_manager(self):
        return self._state_manager

    @property
    def failed_tasks(self) -> list[str]:
        return self._outcomes.failed_tasks

    # ── Helpers ───────────────────────────────────────────────────

    def block_fix_card(self, incident: Incident) -> None:
        board = self._distributor.board
        fix_card = board.card_by_id(incident.fix_card_id)
        if fix_card and fix_card.action != Action.BLOCKED:
            fix_card.block()
            board.save_card(fix_card)
            self._distributor.release_card(fix_card.id)

    def send_incident_telegram(self, incident: Incident, message: str) -> None:
        header = f"INCIDENT {incident.id} ({incident.error_type})\n"
        send_telegram_message(
            header + message,
            self.log_path,
            orc_root=Path(self.workdir),
        )

    def scale_down_workers(self, keep: int = 1) -> tuple[int, list[str]]:
        with self._slots_lock:
            worker_slots = [
                s for s in self._slots.values()
                if (s.role or "worker") == "worker"
                and s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
            ]
        original_count = len(worker_slots)
        if original_count <= keep:
            return original_count, []

        worker_slots.sort(key=lambda s: (0 if s.status == SlotStatus.RUNNING else 1))
        to_remove = worker_slots[keep:]

        removed_ids = []
        for s in to_remove:
            self._session_controller.remove_session(s.session_id)
            removed_ids.append(s.session_id)
        return original_count, removed_ids

    def wait_slots_closed(self, session_ids: list[str], timeout: float = 60.0) -> bool:
        deadline = time.time() + timeout
        remaining = set(session_ids)
        while remaining and time.time() < deadline:
            with self._slots_lock:
                still_open = {
                    sid for sid in remaining
                    if sid in self._slots and self._slots[sid].status not in (SlotStatus.CLOSED,)
                }
            remaining = still_open
            if remaining:
                self.sleep_fn(1.0)
        return len(remaining) == 0

    def scale_up_workers(self, target_count: int) -> list[str]:
        with self._slots_lock:
            current_workers = sum(
                1 for s in self._slots.values()
                if (s.role or "worker") == "worker"
                and s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
            )
        new_ids = []
        to_add = max(0, target_count - current_workers)
        for _ in range(to_add):
            if is_stop_requested():
                break
            sid = self._session_controller.add_session()
            if sid:
                new_ids.append(sid)
            self.sleep_fn(STAGGER_DELAY_SECONDS)
        return new_ids
