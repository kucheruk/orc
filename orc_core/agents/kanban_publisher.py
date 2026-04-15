#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge between kanban orchestrator and TUI: publishes board snapshots and journal events."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Optional

from ..board.kanban_snapshot import JournalEntry, KanbanBoardSnapshot, build_board_snapshot

if TYPE_CHECKING:
    from ..board.kanban_board import KanbanBoard
    from ..models.monitor_dto import MonitorSnapshot


class KanbanPublisher:
    """Collects board state and journal events, pushes them to TUI callbacks."""

    def __init__(self) -> None:
        self.board_callback: Optional[Callable[[KanbanBoardSnapshot], None]] = None
        self.journal_callback: Optional[Callable[[JournalEntry], None]] = None
        self._started_at: float = 0.0

    def set_started_at(self, t: float) -> None:
        self._started_at = t

    def publish_board(
        self,
        board: "KanbanBoard",
        session_snapshots: dict[str, "MonitorSnapshot"],
    ) -> None:
        if not self.board_callback:
            return
        snapshot = build_board_snapshot(board, session_snapshots, self._started_at)
        self.board_callback(snapshot)

    # ── Journal convenience methods ─────────────────────────────

    def log_move(self, card_id: str, from_stage: str, to_stage: str, reason: str = "") -> None:
        extra = f" ({reason})" if reason else ""
        self.emit("move", card_id, f"{card_id} {from_stage} -> {to_stage}{extra}")

    def log_roi(self, card_id: str, value: int, effort: int, roi: float) -> None:
        self.emit("roi", card_id, f"{card_id} ROI={roi} (value={value}/effort={effort})")

    def log_complete(self, card_id: str, role: str, elapsed_seconds: float) -> None:
        mins = elapsed_seconds / 60.0
        self.emit("complete", card_id, f"{card_id} {role} finished ({mins:.1f}m)")

    def log_escalate(self, card_id: str, message: str) -> None:
        self.emit("escalate", card_id, f"{card_id} {message}")

    def log_inbox(self, card_id: str, title: str) -> None:
        self.emit("inbox", card_id, f"{card_id} added to inbox: {title}")

    def log_arbitration(self, card_id: str, decision: str) -> None:
        self.emit("arbitration", card_id, f"{card_id} teamlead: {decision}")

    def log_unblock(self, card_id: str, directive: str) -> None:
        extra = f": {directive}" if directive else ""
        self.emit("approval", card_id, f"{card_id} unblocked by human{extra}")

    def log_incident(self, incident_id: str, message: str) -> None:
        self.emit("incident", "", f"[{incident_id}] {message}")

    def log_action_change(self, card_id: str, old_action: str, new_action: str, role: str) -> None:
        self.emit("action", card_id, f"{card_id} {old_action} -> {new_action} (by {role})")

    def log_assign(self, card_id: str, role: str, agent_id: str) -> None:
        self.emit("assign", card_id, f"{card_id} assigned to {agent_id} as {role}")

    def emit(self, category: str, card_id: str, message: str) -> None:
        if not self.journal_callback:
            return
        entry = JournalEntry(
            timestamp=time.time(),
            category=category,
            card_id=card_id,
            message=message,
        )
        self.journal_callback(entry)
