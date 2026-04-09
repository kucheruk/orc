#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thread-safe kanban work distributor: wraps PullSystem + board for concurrent workers."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from .kanban_board import KanbanBoard
from .kanban_card import KanbanCard
from .kanban_pull import WorkAssignment, find_next_work, find_teamlead_work

_logger = logging.getLogger(__name__)

LOOP_THRESHOLD = 2
ESCALATION_THRESHOLD = 4


class KanbanDistributor:
    """Thread-safe distributor that assigns cards to worker sessions."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._board = KanbanBoard(tasks_dir)
        self._lock = threading.Lock()

    @property
    def board(self) -> KanbanBoard:
        return self._board

    def refresh(self) -> None:
        with self._lock:
            self._board.refresh()

    def pick_worker_task(self, worker_id: str) -> Optional[WorkAssignment]:
        """Atomically find and assign the best available work to a worker."""
        with self._lock:
            assignment = find_next_work(self._board)
            if assignment is None:
                self._log_why_no_work(worker_id)
                return None
            self._board.assign_agent(assignment.card, worker_id)
            _logger.info(
                "Assigned %s to %s (role=%s, stage=%s)",
                assignment.card.id, worker_id, assignment.role, assignment.card.stage,
            )
            return assignment

    def _log_why_no_work(self, worker_id: str) -> None:
        """Log diagnostic info when no work is found."""
        from .kanban_constants import STAGES, Action
        diag: list[str] = []
        for stage in STAGES:
            cards = self._board.cards_in_stage(stage)
            if not cards:
                continue
            assigned = sum(1 for c in cards if c.assigned_agent)
            unassigned = len(cards) - assigned
            actions = {}
            for c in cards:
                key = c.action + ("*" if c.assigned_agent else "")
                actions[key] = actions.get(key, 0) + 1
            action_str = " ".join(f"{k}={v}" for k, v in sorted(actions.items()))
            diag.append(f"{stage}: {len(cards)} ({unassigned} free) [{action_str}]")
        _logger.info("No work for %s: %s", worker_id, "; ".join(diag) or "board empty")

    def pick_teamlead_task(self, agent_id: str) -> Optional[KanbanCard]:
        """Atomically find and assign a card needing teamlead arbitration."""
        with self._lock:
            card = find_teamlead_work(self._board, LOOP_THRESHOLD)
            if card is None:
                return None
            self._board.assign_agent(card, agent_id)
            _logger.info("Assigned %s to teamlead %s (loop=%d)", card.id, agent_id, card.loop_count)
            return card

    def release_card(self, card_id: str) -> None:
        """Release a card's agent assignment (e.g., on failure/timeout)."""
        with self._lock:
            card = self._board.card_by_id(card_id)
            if card:
                self._board.release_agent(card)
                _logger.info("Released card %s from agent", card_id)

    def needs_escalation(self, card: KanbanCard) -> bool:
        return card.loop_count >= ESCALATION_THRESHOLD

    def get_progress(self) -> tuple[int, int, int]:
        """Returns (done, in_progress, total) across the board."""
        with self._lock:
            cards = self._board.cards
            done = sum(1 for c in cards if c.stage == "8_Done")
            in_progress = sum(1 for c in cards if c.assigned_agent)
            return done, in_progress, len(cards)

    def has_remaining_work(self) -> bool:
        """Check if there are any cards not in Done."""
        with self._lock:
            return any(c.stage != "8_Done" for c in self._board.cards)
