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
from ..infra.adapters.fs_card_repository import FsCardRepository
from .stage_constants import STAGE_DONE
from .kanban_pull import WorkAssignment, find_next_work, find_teamlead_work

_logger = logging.getLogger(__name__)

LOOP_THRESHOLD = 2
ESCALATION_THRESHOLD = 4


class KanbanDistributor:
    """Thread-safe distributor that assigns cards to worker sessions."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._board = KanbanBoard(tasks_dir, repo=FsCardRepository())
        self._lock = threading.Lock()

    @property
    def board(self) -> KanbanBoard:
        return self._board

    def refresh(self) -> None:
        with self._lock:
            self._board.refresh()

    def pick_worker_task(self, worker_id: str) -> Optional[WorkAssignment]:
        """Atomically find and assign the best available work to a worker.

        Returns None if no work is available. Use ``diagnose_no_work`` for the reason.
        """
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

    def diagnose_no_work(self) -> str:
        """Return a human-readable reason why no work can be picked.

        Safe to call at any time — does not depend on prior ``pick_worker_task`` state.
        """
        with self._lock:
            non_done = [c for c in self._board.cards if c.stage != STAGE_DONE]
            if not non_done:
                return "board empty — all cards Done"
            assigned = [c for c in non_done if c.assigned_agent]
            unassigned = [c for c in non_done if not c.assigned_agent]
            if not unassigned:
                agents = ", ".join(sorted({c.assigned_agent for c in assigned}))
                return f"all {len(assigned)} active cards assigned to other agents ({agents})"
            # There are unassigned cards but find_next_work returned None
            deadlock = self._board.detect_wip_deadlock()
            if deadlock:
                return deadlock
            # Summarize why unassigned cards can't be picked
            reasons: list[str] = []
            from .limits_constants import WIP_STAGES
            for c in unassigned:
                if c.stage in WIP_STAGES and not self._board.has_wip_room(c.stage):
                    reasons.append(f"{c.id}: WIP full in {c.stage}")
                elif self._board.has_unmet_dependencies(c):
                    reasons.append(f"{c.id}: unmet deps")
                else:
                    reasons.append(f"{c.id}: action={c.action} in {c.stage} — no matching role in pull order")
            return "; ".join(reasons[:5]) if reasons else "unknown — no assignable work found"

    def _log_why_no_work(self, worker_id: str) -> None:
        """Log diagnostic info when no work is found."""
        from .stage_constants import STAGES
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
            done = sum(1 for c in cards if c.stage == STAGE_DONE)
            in_progress = sum(1 for c in cards if c.assigned_agent)
            return done, in_progress, len(cards)

    def has_remaining_work(self) -> bool:
        """Check if there are any cards not in Done."""
        with self._lock:
            return any(c.stage != STAGE_DONE for c in self._board.cards)
