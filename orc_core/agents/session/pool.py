#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session slot pool: manages worker/teamlead thread lifecycle."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from ...log import log_event
from ...contracts.session import MonitorSnapshot
from ...quit_signal import is_stop_requested, is_session_stop_requested
from ..infra.publisher import KanbanPublisher
from .types import (
    MAX_SESSIONS,
    SHUTDOWN_JOIN_TIMEOUT_SECONDS,
    SessionSlot,
    SlotStatus,
    next_session_id,
)

_logger = logging.getLogger(__name__)

SnapshotPublisher = Callable[[str, Optional[MonitorSnapshot]], None]


class SessionPool:
    """Manages session slots: create, launch, reap, restart, shutdown."""

    def __init__(
        self,
        *,
        max_sessions: int,
        publisher: KanbanPublisher,
        log_path,
        sleep_fn: Callable[[float], None],
    ) -> None:
        self.max_sessions = max(2, min(max_sessions, MAX_SESSIONS))
        self.publisher = publisher
        self.log_path = log_path
        self.sleep_fn = sleep_fn
        self.snapshot_publisher: Optional[SnapshotPublisher] = None

        self._slots: dict[str, SessionSlot] = {}
        self._slots_lock = threading.Lock()
        self._session_snapshots: dict[str, MonitorSnapshot] = {}

    # ── Accessors (for IncidentManager compatibility) ────────────

    @property
    def slots(self) -> dict[str, SessionSlot]:
        return self._slots

    @property
    def slots_lock(self) -> threading.Lock:
        return self._slots_lock

    @property
    def session_snapshots(self) -> dict[str, MonitorSnapshot]:
        return self._session_snapshots

    # ── Public API ───────────────────────────────────────────────

    def start_session(
        self,
        role: str,
        target: Callable[[SessionSlot], None],
    ) -> Optional[str]:
        with self._slots_lock:
            active = sum(
                1 for s in self._slots.values()
                if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING, SlotStatus.CLOSING)
            )
            if active >= self.max_sessions:
                self.publisher.emit(
                    "system", "",
                    f"Cannot add agent: {active}/{self.max_sessions} slots used",
                )
                return None
            sid = next_session_id()
            slot = SessionSlot(session_id=sid)
            self._slots[sid] = slot
        slot.role = role
        self._launch_thread(slot, target)
        self.publisher.emit("system", "", f"{sid} session created (role={role})")
        if self.snapshot_publisher:
            self.snapshot_publisher(sid, None)
        log_event(self.log_path, "INFO", "kanban session started", session_id=sid, role=role)
        return sid

    def request_add(self, target: Callable[[SessionSlot], None]) -> Optional[str]:
        return self.start_session(role="worker", target=target)

    def request_remove(self, session_id: str = "") -> None:
        with self._slots_lock:
            candidates = [
                s for s in self._slots.values()
                if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
            ]
            if session_id:
                slot = next((s for s in candidates if s.session_id == session_id), None)
            else:
                slot = candidates[-1] if candidates else None
        if slot:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSING
            log_event(self.log_path, "INFO", "session closing", session_id=slot.session_id)

    def reap_finished(self) -> None:
        with self._slots_lock:
            for slot in self._slots.values():
                if slot.thread and not slot.thread.is_alive() and slot.status == SlotStatus.RUNNING:
                    slot.status = SlotStatus.CLOSED
                    slot.thread = None

    def restart_idle(self, target: Callable[[SessionSlot], None]) -> None:
        with self._slots_lock:
            closed = [s for s in self._slots.values() if s.status == SlotStatus.CLOSED]
        for slot in closed:
            self._launch_thread(slot, target)

    def has_active(self) -> bool:
        with self._slots_lock:
            return any(
                s.status in (SlotStatus.IDLE, SlotStatus.RUNNING, SlotStatus.CLOSING)
                or (s.thread is not None and s.thread.is_alive())
                for s in self._slots.values()
            )

    def active_tasks_by_session(self) -> dict[str, str]:
        """Map of session_id -> task_id for slots currently processing a card.

        Replaces the pre-B0 behavior of reading parallel/*/active-task.json
        files from the runtime state root — the in-memory pool is the
        authoritative source for "which slot owns which card".
        """
        with self._slots_lock:
            result: dict[str, str] = {}
            for sid, slot in self._slots.items():
                if slot.status not in (SlotStatus.RUNNING, SlotStatus.CLOSING):
                    continue
                task = slot.task
                if task is None:
                    continue
                task_id = str(getattr(task, "task_id", "") or "").strip()
                if task_id:
                    result[sid] = task_id
            return result

    def running_info(self) -> str:
        with self._slots_lock:
            running = [
                s for s in self._slots.values()
                if s.status == SlotStatus.RUNNING and s.thread and s.thread.is_alive()
            ]
        if not running:
            return ""
        parts = []
        for s in running:
            if s.task:
                parts.append(f"{s.session_id}({s.task.text})")
            else:
                parts.append(f"{s.session_id}(idle)")
        return ", ".join(parts)

    def should_continue(self, slot: SessionSlot) -> bool:
        return (
            not is_stop_requested()
            and not is_session_stop_requested(slot.session_id)
            and slot.status != SlotStatus.CLOSING
        )

    def publish_snapshot(self, session_id: str, snapshot: MonitorSnapshot) -> None:
        self._session_snapshots[session_id] = snapshot
        if self.snapshot_publisher:
            self.snapshot_publisher(session_id, snapshot)

    def shutdown_threads(self) -> None:
        with self._slots_lock:
            for s in self._slots.values():
                s.status = SlotStatus.CLOSING
            threads = [(s.session_id, s.thread) for s in self._slots.values() if s.thread]
        total = len(threads)
        if total:
            self.publisher.emit("system", "", f"Shutting down {total} agents...")
        for i, (sid, t) in enumerate(threads, 1):
            self.publisher.emit("system", "", f"Waiting for {sid} ({i}/{total})...")
            t.join(timeout=SHUTDOWN_JOIN_TIMEOUT_SECONDS)
            if t.is_alive():
                self.publisher.emit("system", "", f"{sid} still running, skipping")
            else:
                self.publisher.emit("system", "", f"{sid} stopped ({total - i} remaining)")
        if total:
            self.publisher.emit("system", "", "All agents stopped")

    # ── Internal ─────────────────────────────────────────────────

    def _launch_thread(self, slot: SessionSlot, target: Callable[[SessionSlot], None]) -> None:
        thread = threading.Thread(
            target=target, args=(slot,), daemon=True,
            name=f"kanban-{slot.session_id}",
        )
        with self._slots_lock:
            slot.thread = thread
            slot.status = SlotStatus.RUNNING
        thread.start()
