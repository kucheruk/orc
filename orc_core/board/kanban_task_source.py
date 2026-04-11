#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge between KanbanBoard and the existing TaskSource protocol."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .kanban_board import KanbanBoard
from .kanban_constants import STAGE_DONE
from ..tasks.task_source import Task


class KanbanTaskSource:
    """Implements the TaskSource protocol using a kanban board.

    Maps kanban cards to Task objects so existing code (TaskExecutionEngine,
    TUI progress display) can work with kanban mode without changes.
    """

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._board = KanbanBoard(tasks_dir)

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
        card = self._board.card_by_id(task_id)
        if card is None:
            return False
        if card.stage != STAGE_DONE:
            self._board.move_card(card, STAGE_DONE, reason="task completed")
        return True
