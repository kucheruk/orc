#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge between KanbanBoard and the existing TaskSource protocol."""

from __future__ import annotations

from typing import List, Optional

import logging

from .kanban_board import KanbanBoard
from .stage_constants import STAGE_DONE
from ..tasks.dto import Task

_logger = logging.getLogger(__name__)


class KanbanTaskSource:
    """Implements the TaskSource protocol using a kanban board.

    Maps kanban cards to Task objects so existing code (TaskExecutionEngine,
    TUI progress display) can work with kanban mode without changes.
    """

    def __init__(self, board: KanbanBoard) -> None:
        self._board = board
        self._tasks_dir = board.tasks_dir

    @property
    def board(self) -> KanbanBoard:
        return self._board

    def refresh(self) -> None:
        self._board.refresh()

    def list_tasks(self) -> List[Task]:
        return [
            Task(task_id=c.id, text=c.title or c.id, done=(c.stage == STAGE_DONE))
            for c in self._board.cards
        ]

    def get_open_tasks(self) -> List[Task]:
        return [t for t in self.list_tasks() if not t.done]

    def get_first_open_task(self) -> Optional[Task]:
        open_tasks = self.get_open_tasks()
        return open_tasks[0] if open_tasks else None

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        card = self._board.card_by_id(task_id)
        if card is None:
            return None
        return Task(task_id=card.id, text=card.title or card.id, done=(card.stage == STAGE_DONE))

    def is_task_done(self, task_id: str) -> bool:
        card = self._board.card_by_id(task_id)
        return card is not None and card.stage == STAGE_DONE

    def mark_task_done(self, task_id: str) -> bool:
        # Legacy protocol hook from the markdown-backlog era. On the kanban
        # board the ONLY legitimate path to STAGE_DONE is the integrator
        # flow (finalize_completed_worktree after a successful squash merge).
        # Refuse to bypass that — otherwise a card can reach 8_Done without
        # its source code landing on the main branch.
        card = self._board.card_by_id(task_id)
        if card is None:
            return False
        if card.stage == STAGE_DONE:
            return True
        _logger.warning(
            "Refusing to move %s to STAGE_DONE via legacy mark_task_done; "
            "kanban cards must go through the integrator path.",
            task_id,
        )
        return False
