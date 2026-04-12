#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incident state machine: detect worker crashes, triage, inject fix, scale workers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from ..board.kanban_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_REVIEW,
    Action,
)
from ..tasks.task_execution_types import TaskExecutionStatus
from ..infra.logging import log_event
from ..notifications.notify import send_telegram_message
from ..infra.quit_signal import is_stop_requested
from ..infra.session_types import (
    STAGGER_DELAY_SECONDS,
    SessionSlot,
    SlotStatus,
)
from ..tasks.task_source import Task
from .teamlead_incident import (
    DECISION_FILENAME,
    FIX_CARD_PREFIX,
    INCIDENT_FIX_TIMEOUT,
    SCALE_DOWN_WAIT_TIMEOUT,
    Incident,
    IncidentPhase,
    build_incident_prompt,
    fallback_decision,
    parse_incident_decision,
)

from .kanban_protocols import RunnerStateManager, SessionController

if TYPE_CHECKING:
    import threading

    from ..board.kanban_distributor import KanbanDistributor
    from .kanban_publisher import KanbanPublisher
    from ..tasks.task_execution import TaskExecutionEngine


class IncidentManager:
    """Incident state machine extracted from KanbanSessionManager.

    Handles: detect_anomaly → scale_down → triage → inject_fix → wait_for_fix → scale_up.
    """

    def __init__(
        self,
        *,
        distributor: KanbanDistributor,
        publisher: KanbanPublisher,
        engine: TaskExecutionEngine,
        slots: dict[str, SessionSlot],
        slots_lock: threading.Lock,
        failed_tasks: list[str],
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
        self._failed_tasks = failed_tasks
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
        """Process one step of the incident state machine."""
        _PHASE_DISPATCH = {
            IncidentPhase.SCALE_DOWN: lambda: self._incident_scale_down(incident),
            IncidentPhase.TRIAGE: lambda: self._incident_triage(slot, incident),
            IncidentPhase.INJECT_FIX: lambda: self._incident_inject_fix(incident),
            IncidentPhase.WAIT_FOR_FIX: lambda: self._incident_wait_for_fix(incident),
            IncidentPhase.SCALE_UP: lambda: self._incident_scale_up(incident),
            IncidentPhase.NOTIFY_HUMAN: lambda: self._incident_notify_human(incident),
        }
        handler = _PHASE_DISPATCH.get(incident.phase)
        if handler is None:
            log_event(self.log_path, "ERROR", "unknown incident phase",
                      incident_id=incident.id, phase=str(incident.phase))
            return None
        return handler()

    # ── Phase handlers ───────────────────────────────────────────

    def _incident_scale_down(self, incident: Incident) -> Incident:
        original_count, removed_ids = self._scale_down_workers(keep=1)
        intended_count = self.max_sessions - 1
        incident.original_worker_count = max(original_count, intended_count)
        incident.removed_session_ids = removed_ids
        self.publisher.log_incident(
            incident.id,
            f"Scaling down: {original_count} → 1 worker (removed {len(removed_ids)})",
        )
        log_event(self.log_path, "INFO", "incident scale_down",
                  incident_id=incident.id, original=original_count, removed=len(removed_ids))
        if removed_ids:
            self._wait_slots_closed(removed_ids, timeout=SCALE_DOWN_WAIT_TIMEOUT)
        incident.phase = IncidentPhase.TRIAGE
        return incident

    def _incident_triage(self, slot: SessionSlot, incident: Incident) -> Incident:
        sid = slot.session_id
        board = self._distributor.board
        source_card = board.card_by_id(incident.source_task_id) if incident.source_task_id else None

        orc_root = Path(self.workdir) / ".orc"
        orc_root.mkdir(parents=True, exist_ok=True)
        decision_path = orc_root / DECISION_FILENAME

        prompt = build_incident_prompt(incident, board, source_card, str(decision_path), orc_root)
        task = Task(task_id=f"triage-{incident.id}", text=f"[TL] Triage {incident.id}", done=False)
        slot.task = task

        self.publisher.log_incident(incident.id, "Running AI triage agent...")
        result = self.engine.execute(self._state_manager.make_request(task, prompt, self.workdir, sid, False, 600.0))

        try:
            if result and result.status == TaskExecutionStatus.COMPLETED and decision_path.exists():
                decision = parse_incident_decision(decision_path)
            else:
                self.publisher.log_incident(incident.id, "AI triage failed, using fallback")
                log_event(self.log_path, "WARN", "triage agent failed, using fallback",
                          incident_id=incident.id)
                decision = fallback_decision(incident)
        except Exception as exc:
            self.publisher.log_incident(incident.id, f"Decision parse failed: {exc}, using fallback")
            log_event(self.log_path, "WARN", "decision parse failed",
                      incident_id=incident.id, error=str(exc),
                      error_type=type(exc).__name__)
            decision = fallback_decision(incident)
        finally:
            for cleanup_path in (decision_path, orc_root / "incident-traceback.txt"):
                if cleanup_path.exists():
                    try:
                        cleanup_path.unlink()
                    except OSError:
                        pass

        incident.error_class = decision.classification
        incident.target_role = decision.target_role
        incident.fix_title = decision.fix_title
        incident.fix_body = decision.body

        self.publisher.log_incident(
            incident.id,
            f"Triage result: {decision.classification}, role={decision.target_role}, "
            f"title={decision.fix_title[:80]}",
        )
        log_event(self.log_path, "INFO", "triage complete",
                  incident_id=incident.id, classification=decision.classification,
                  target_role=decision.target_role)

        if decision.classification == "orc":
            incident.phase = IncidentPhase.NOTIFY_HUMAN
        else:
            incident.phase = IncidentPhase.INJECT_FIX
        return incident

    def _incident_inject_fix(self, incident: Incident) -> Incident:
        board = self._distributor.board
        base = incident.source_task_id or "unknown"
        fix_card_id = f"{FIX_CARD_PREFIX}{base}-{incident.id}"

        _ROLE_PLACEMENT: dict[str, tuple[str, str]] = {
            "coder":      (STAGE_CODING,   Action.CODING),
            "architect":  (STAGE_ESTIMATE, Action.ARCHITECT),
            "reviewer":   (STAGE_REVIEW,   Action.REVIEWING),
            "integrator": (STAGE_HANDOFF,  Action.INTEGRATING),
        }
        stage, action = _ROLE_PLACEMENT.get(incident.target_role, (STAGE_CODING, Action.CODING))

        board.create_expedite_card(
            card_id=fix_card_id,
            title=incident.fix_title,
            body=incident.fix_body,
            stage=stage,
            action=action,
            cos_justification=f"Incident {incident.id}: {incident.error_type}",
        )
        incident.fix_card_id = fix_card_id
        incident.fix_started_at = time.time()

        self.publisher.log_incident(
            incident.id,
            f"Fix card {fix_card_id} created in {stage} (role={incident.target_role})",
        )
        log_event(self.log_path, "INFO", "fix card injected",
                  incident_id=incident.id, fix_card_id=fix_card_id,
                  stage=stage, target_role=incident.target_role)

        incident.phase = IncidentPhase.WAIT_FOR_FIX
        return incident

    def _incident_wait_for_fix(self, incident: Incident) -> Optional[Incident]:
        board = self._distributor.board
        fix_card = board.card_by_id(incident.fix_card_id)

        if fix_card and fix_card.stage == STAGE_DONE:
            self.publisher.log_incident(incident.id, f"Fix {incident.fix_card_id} completed!")
            log_event(self.log_path, "INFO", "fix completed",
                      incident_id=incident.id, fix_card_id=incident.fix_card_id)
            incident.phase = IncidentPhase.SCALE_UP
            return incident

        if incident.fix_card_id in self._failed_tasks:
            self.publisher.log_incident(
                incident.id,
                f"Fix card {incident.fix_card_id} itself failed — escalating to human",
            )
            self._block_fix_card(incident)
            self._send_incident_telegram(
                incident,
                f"Fix card {incident.fix_card_id} failed while trying to resolve "
                f"incident {incident.id}.\n"
                f"Original error: {incident.error_message[:500]}",
            )
            self._scale_up_workers(incident.original_worker_count)
            return None

        elapsed = time.time() - incident.fix_started_at
        if elapsed > INCIDENT_FIX_TIMEOUT:
            self.publisher.log_incident(
                incident.id,
                f"Fix timeout ({INCIDENT_FIX_TIMEOUT:.0f}s) — escalating to human",
            )
            self._block_fix_card(incident)
            self._send_incident_telegram(
                incident,
                f"Fix card {incident.fix_card_id} timed out after {elapsed:.0f}s.\n"
                f"Incident {incident.id}: {incident.error_message[:500]}",
            )
            self._scale_up_workers(incident.original_worker_count)
            return None

        return incident  # Keep waiting

    def _incident_scale_up(self, incident: Incident) -> None:
        new_ids = self._scale_up_workers(incident.original_worker_count)
        self.publisher.log_incident(
            incident.id,
            f"Scaling up: restored to {incident.original_worker_count} workers "
            f"(added {len(new_ids)})",
        )
        log_event(self.log_path, "INFO", "incident scale_up",
                  incident_id=incident.id, target=incident.original_worker_count,
                  added=len(new_ids))
        return None

    def _incident_notify_human(self, incident: Incident) -> None:
        self.publisher.log_incident(incident.id, "ORC error — notifying human via Telegram")

        message = incident.fix_body or (
            f"ORC BUG in incident {incident.id}\n"
            f"Error: {incident.error_message}\n"
            f"Traceback:\n{incident.traceback[:1500]}"
        )
        self._send_incident_telegram(incident, message)

        if incident.source_task_id:
            board = self._distributor.board
            card = board.card_by_id(incident.source_task_id)
            if card and card.action != Action.BLOCKED:
                card.block()
                board.save_card(card)
                self._distributor.release_card(card.id)

        log_event(self.log_path, "WARN", "orc error notified, workers remain scaled down",
                  incident_id=incident.id, source_task=incident.source_task_id)
        return None

    # ── Helpers ───────────────────────────────────────────────────

    def _block_fix_card(self, incident: Incident) -> None:
        board = self._distributor.board
        fix_card = board.card_by_id(incident.fix_card_id)
        if fix_card and fix_card.action != Action.BLOCKED:
            fix_card.block()
            board.save_card(fix_card)
            self._distributor.release_card(fix_card.id)

    def _send_incident_telegram(self, incident: Incident, message: str) -> None:
        header = f"INCIDENT {incident.id} ({incident.error_type})\n"
        send_telegram_message(
            header + message,
            self.log_path,
            orc_root=Path(self.workdir),
        )

    def _scale_down_workers(self, keep: int = 1) -> tuple[int, list[str]]:
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

    def _wait_slots_closed(self, session_ids: list[str], timeout: float = 60.0) -> bool:
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

    def _scale_up_workers(self, target_count: int) -> list[str]:
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
